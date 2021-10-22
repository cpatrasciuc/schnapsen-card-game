# Tuning MctsPlayer

TODO: add a table of contents

## The problem

The initial version of the MctsPlayer lost 70 out of 100 bummerls against
the HeuristicPlayer. After switching from `best_action_frequency` to
`max_average_ucb_across_root_nodes`, the results against the HeuristicPlayer
were the following:

| Cheater | Time Limit | Bummerls won out of 100 | Games won over 100 bummerls |
|:-------:|:----------:|:-----------------------:|:---------------------------:|
| True | 1 sec | **<span style="color:green">77% [67.85%, 84.16%]</span>** | <span style="color:green">**66.05% [62.15%, 69.74%]**</span> (393 vs 292) |
| True | 5 sec | **<span style="color:green">85% [76.72%, 90.69%]</span>** | <span style="color:green">**70.19% [66.30%, 73.81%]**</span> (398 vs 169) |
| False | 1 sec | 55% [45.24%, 64.39%] | 52.76% [48.92%, 56.57%] (344 vs 308) |
| False | 5 sec | **<span style="color:green">60% [50.20%, 69.06%]</span>** | <span style="color:green">**55.02% [51.20%, 58.78%]**</span> (362 vs 296) |

In the perfect information scenarios (cheater=True), the MctsPlayer is able to
beat the HeuristicPlayer. In the imperfect information scenarios there
is no clear difference between the two players.

**The goal is to make the MctsPlayer significantly better than the
HeuristicPlayer in imperfect information scenarios.** 

The next sections experiment with possible changes that could improve the
MctsPlayer's performance.

## Initial analysis

I started by measuring how much (process-)time it takes to run a given number of
Mcts iterations for a perfect information scenario.

![iterations_vs_time_plot](https://github.com/cpatrasciuc/schnapsen-card-game/blob/ac6328f5a043ce946fb59c2303a5b32fe7ce224b/src/ai/eval/data/iterations_and_time_i7.png)

In the simulations against the HeuristicPlayer, the MctsPlayer was configured to
use 1 or 5 seconds to process at most 100 permutations using a pool of 8
workers. Based on the plot above, this means that at the beginning of a game the
computational budget is:

| Total time limit | Time limit for one permutation | Iterations for one permutation |
| :--------------: | :----------------------------: | :----------------------------: |
| 1 second | 0.08 seconds | 10-20 |
| 5 seconds | 0.38 seconds | 40-80 |

I verified this by running the MctsPlayer on 100 initial game states (seed
between 0 and 99) and logging the number of iterations per permutation. The
results are aligned with the expectations:

|       | Time limit: 1 second | Time limit: 5 seconds |
| :---: | :------------------: | :-------------------: |
| **mean** | **9.78** | **54.82** |
| std | 3.09 | 16.37 |
| min | 1 | 19 |
| 25% | 8 | 43 |
| 50% | 9 | 52 |
| 75% | 11 | 64 |
| max | 49 | 196 |

I plotted the evolution of the scores for each player action across time for a
couple of end-game scenarios as well as initial game states ([plot](https://raw.githubusercontent.com/cpatrasciuc/schnapsen-card-game/138670a600e4c23489988699469a37af3b158749/src/ai/eval/data/mcts_convergence.png)).
For the end-game scenarios the scores correctly converge to their final value.
For the initial game states, there is some expected noise in the first
iterations, but then the relative order of the actions seems to stabilize after
~2000 iterations.

Unfortunately, given the low number of iterations allocated for one permutation,
in the early stages of the game the MctsPlayer does not run enough iterations
for the result to be meaningful. We are still in the noisy area.

The hypothesis is that at the beginning of the game the MctsPlayer is playing
more or less randomly, and then it tries to compensate for the possible bad
decisions in the end-stages of the game, when there are fewer permutations to
consider.

As a result of this initial debugging, the ideas to experiment with are:

- [x] Reduce CPU usage, so we can run more iterations within the budget
- [x] Pick the best child during the selection phase and balance exploration versus exploitation
- [x] Find the best combination of max_iterations and max_permutations for a fixed computational budget
- [x] When a node is expanded for the first time, start with the action deemed best by the HeuristicPlayer
- [x] Improve the aggregation of scores from all Mcts trees
- [x] Reuse the nodes from the previous decisions instead of always starting from scratch
- [x] Use Information Set Monte Carlo Tree Search

> **Computational budget: `time_limit_sec` vs `max_iterations`**
>
> Limiting the time used by the MctsPlayer makes it difficult to compare its
> performance across different runs and/or different machines. If we use raw time,
> the number of iterations that the player manages to run in the given amount of
> time depends on the system's load. If we use process time and our workers are
> scheduled sequentially on the same core(s), the actual time required to find a
> move will be larger than expected (as perceived by a human player). In both
> case the performance cannot be compared across different machines.
> 
> At this point I decided to limit the maximum number of iterations that the
> Mcts algorithm is allowed to perform before it must pick a move 
> ([commit](https://github.com/cpatrasciuc/schnapsen-card-game/commit/d267004c089d9d2ba15d4ed6d96de0b98b3d33ca)).
> This makes the performance of the MctsPlayer comparable across different runs, even
> across different machines.

## Reduce CPU usage

I added CPU profiling to [`iterations_and_time.py`](https://github.com/cpatrasciuc/schnapsen-card-game/blob/main/src/ai/eval/mcts_iterations_and_time.py).
The [first results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/e19317e77cf9533f813ae651b2d996f153074e4b/src/ai/eval/data/iterations_and_time.profile.txt)
showed that 88% of the time is spent in `copy.deepcopy()`.

### Step 1: Replace copy.deepcopy() with GameState.deep_copy()

I added my own `GameState.deep_copy()`, to create a deep copy of itself. I
measured its speed in `GameStateCopyTest`. The results are as follows:

| Function | Time (ms) |
| :------: | :--------: |
| `copy.copy(game_state)` | 0.0030352 |
| `game_state.deep_copy()` | 0.0291062 |
| `pickle.loads(pickle.dumps(game_state))` | 0.0806335 |
| `copy.deepcopy(game_state)` | 0.3028298 |

Overall, this change allows the Mcts algorithm to run ~5x more iterations in the
same amount of time. However, [the new CPU profile](https://github.com/cpatrasciuc/schnapsen-card-game/blob/95eacb321110269495dbee47d5a8f185acb66c04/src/ai/eval/data/iterations_and_time.profile.txt)
shows that the new `GameState.deep_copy()` method takes ~66% of the time.

### Step 2: Replace deep copies with shallow copies

Instead of making deep copies for the game states to be stored in each tree
node, I modified `PlayerAction.execute()` to create a (shallow) copy of the
input/parent game state that shares as many fields as possible with it
([commit](https://github.com/cpatrasciuc/schnapsen-card-game/commit/f263b24c8b7ab8c66b3a0ed8cd4b167d4579ed8)).

Overall, this change allows the Mcts algorithm to run ~2x more iterations in the
same amount of time. The amount of time spent in copying the game state and
executing a player action decreased from 73% (GameState.deep_copy: 66%,
PlayerAction.execute: 7%) to 26% (only PlayerAction.execute).

After these two steps the number of iterations that could be run in 10 seconds
increased from ~2k to ~20k.

![iterations_and_time_i7.png](https://github.com/cpatrasciuc/schnapsen-card-game/blob/d0337e7e31ce813ffb58c011ecd7e45a1d20a253/src/ai/eval/data/iterations_and_time_i7.png)

### Step 3: multiprocessing.Pool overhead

Even if I managed to reduce the CPU usage of the Mcts algorithm (i.e., the
single threaded construction of one tree for a perfect information game state),
it was surprisingly slow in the `SchnapsenApp` for `max_iterations=1000-2000`
and `max_permutations=8-16`.

I measured how much time it takes the MctsPlayer to run a given number of
iterations. It seems that the `multiprocessing.Pool` overhead takes a
significant amount of time, most likely serializing and deserializing the data
between the parent and child processes. The Mcts algorithm is able to run 20k
iterations in ~10 seconds, but when the MctsPlayer runs 8 such algorithms in
parallel using `multiprocessing.Pool` it can only run ~4k iterations in the same
amount of time.

![iterations_and_time_8perm.png](https://github.com/cpatrasciuc/schnapsen-card-game/blob/7257ad01d7d4bd92aa25bea5dd1c19fc0ed4ff42/src/ai/eval/data/iterations_and_time_8perm.png)

I experimented with the following ideas hoping they would reduce this overhead,
but none of them was successful:

* Use `multiprocessing.Pool.imap` or `multiprocessing.Pool.imap_unordered` or
  setting the `chunksize` argument explicitly in these calls.
* Implement my own MctsWorker and MctsWorkerPool (see the `mcts_worker` branch).
  This is similar to the `multiprocessing.Pool` but instead of using a
  single task queue, I split the permutations and directly assign
  them to specific child processes for processing. I tried using both `Pipe` and
  `Queue` to communicate with the children.
* Use the `dill` and `pathos` modules to see if they speed up the pickling.
* Use `ray`. It didn't work out of the box with `venv`. I did not debug further.
* Use `multiprocessing.dummy` just to make sure that threads don't work either.

##### MctsPlayerOptions.first_level_only

One possible solution to reduce the time spent in serializing/deserializing is
to reduce the amount of data passed between the MctsPlayer and the workers. 
There is nothing that can be removed from the data sent to the workers (it's
just the game view and the permutations that have to be processed). The workers
send back the whole tree. Currently, we only need the first level of the tree to
merge the scores across trees and pick the best action. By only sending this
data back to the MctsPlayer, we reduce the amount of data sent from 12Mb to 2Kb
(99.98% reduction). This allows the MctsPlayer to run 1.5-2x more iterations in
the same amount of time ([plot](https://github.com/cpatrasciuc/schnapsen-card-game/blob/7a9a12b607cdbae7e39a62703bc633ef9894c86b/src/ai/eval/data/iterations_and_time_8perm.png)).
The disadvantage of this solution is that we won't be able to
[reuse these nodes/trees](#reuse-the-nodes-from-previous-decisions) later. 

After steps 1-3, the MctsPlayer went from running 800 iterations in 10 seconds
to running 7k iterations in 10 seconds (8 permutations processed on 8 cores).

### Step 4: Use Cython

Even if steps 1-3 made the player ~10x faster, it was still far from being
usable. Based on the initial plots, we require at least 2000 iterations for the
scores to stabilize. In 5 seconds, using 2000 iterations, the player can process
only 8 permutations. I expect this is not enough for the early stages of the
game (no data to prove this, though). At this point I had no ideas on how to
make it even faster in Python, so I decided to write the Mcts algorithm in C/C++
using Cython.

The Cython version of the MctsPlayer can run ~50x more iterations than the
MctsPlayer from step 3 in single-threaded mode. The number of iterations that
could be run in 10 seconds went from ~20k to 1 million. 

![iterations_and_time_i7.png](https://github.com/cpatrasciuc/schnapsen-card-game/blob/1d3ad8f6f77059cd30780c657f861fcec6888be9/src/ai/eval/data/iterations_and_time_i7.png)

**Parallelism:** Since the new implementation is in pure C/C++ and there is
no interaction with Python objects, we could release the GIL and use threads to
process permutations in parallel on multiple cores. Cython has support for
parallelism/threads using OpenMP
([link](https://cython.readthedocs.io/en/latest/src/userguide/parallelism.html)).
I added multi-threading support to the CythonMctsPlayer, but it is slower than
the single threaded-version. While the MctsPlayer becomes faster as we increase
the number of processes in the multiprocessing.Pool, the CythonMctsPlayer
appears to become slower as we increase the number of threads:

| ![mcts_player](https://github.com/cpatrasciuc/schnapsen-card-game/blob/d715610cdebface033f3917ed9a1939d8db2fda1/src/ai/eval/data/num_threads_and_time.png) | ![cython_mcts_player](https://github.com/cpatrasciuc/schnapsen-card-game/blob/36b94e4e25af5e39029e62073768c9d133771157/src/ai/eval/data/num_threads_and_time.png) |
| :------: | :--------: |

I had to stop here because I have no experience with OpenMP debugging/profiling.
However, the single-threaded version of the CythonMctsPlayer is still ~17x
faster than the MctsPlayer that uses 8 processes. The table below shows the time
(seconds) required by each player to run in different scenarios:

|Scenario|MctsPlayer (4k iterations)|CythonMctsPlayer (4k iterations)|CythonMctsPlayer (40k iterations)|
| :---: | :---: | :---: | :---: |
|Mcts algorithm (Python only)|2.43|-|-|
|Cheater player, w/o parallelism|2.37|0.04|0.39|
|Cheater player, w/ parallelism|3.79|0.07|0.51|
|1 permutation, w/o parallelism|2.56|0.23|0.59|
|1 permutation, w/ parallelism|4.01|0.23|0.57|
|8 permutations, w/o parallelism|18.07|0.47|3.15|
|8 permutations, w/ parallelism|7.87|1.27|9.91|
|16 permutations, w/o parallelism|38.82|0.80|6.33|
|16 permutations, w/ parallelism|13.66|2.43|20.17|
|100 permutations, w/o parallelism|-|3.93|-|
|100 permutations, w/ parallelism|-|14.00|-|

### Conclusion and results

I will move forward with using the CythonMctsPlayer in single-threaded mode.
Overall, after steps 1-4, the player went from running 8 permutations x 800
iterations in 10 seconds (using 8 cores) to running 250 permutations x 
4000 iterations in the same amount of time (i.e., 156 times faster).

## Select the best child and balance exploration vs exploitation

During the selection phrase, the initial version of the MctsPlayer, always
picked one of the not-fully-simulated children randomly, for each node. At this
stage, I modified it to always pick the child that maximizes the Upper
Confidence Bound (UCB) formula:

![UCB Formula](https://latex.codecogs.com/svg.latex?%5Cfrac%7BQ_i%7D%7BN_i%7D%20&plus;%20C%5Csqrt%7B%5Cfrac%7B2log%28N_%7Bparent%7D%29%7D%7BN_i%7D%7D)

* The first term represents the average points scored on the paths going through
  the i-th child. This term is the *exploitation* component. It scores high for
  children that gave good results so far.
* The second term is the *exploration* component. It scores high for the
  children that were least-visited until now.
* The exploration parameter *C* controls the balance between exploration and
  exploitation.

### Improvements in the perfect information scenarios

I tried to find a metric that would tell me if this version is better than just
selecting a child randomly. By adding `save_rewards=True` to 
`MctsPlayerOptions`, we store for each possible action (children of the Mcts
root node) a list of all the rewards obtained on the paths going through that
node. Then, I use `scipy.stats.bootstrap` to compute a 95% CI for the mean of
these rewards. The random selection version has roughly the same confidence for
all actions. The exploration-vs-exploitation version, trades some confidence
from the not-so-good actions for a better confidence in the best action's score.

| CI Widths for UCB-based Selection  | CI Widths for Random Selection |
| :------: | :--------: |
| ![ci_widths_best_child](https://github.com/cpatrasciuc/schnapsen-card-game/blob/select_best_child/src/ai/eval/data/mcts_ci_widths_across_game_states_best_child_1000iter.png) | ![ci_widths_random_selection](https://github.com/cpatrasciuc/schnapsen-card-game/blob/select_best_child/src/ai/eval/data/mcts_ci_widths_across_game_states_random_1000iter.png) |

The results above use 30 initial game states and `max_iterations=1000`. They
were obtained using
`mcts_ci_widths_across_multiple_game_states(use_player=False)`.

I verified that improving the confidence in a perfect information scenario
leads to better decisions by running UCB-based Selection vs Random Selection,
with `cheater=True`. The player that uses UCB-based Selection won in **64.40%
[61.38%, 67.31%]** of the cases (out of 1000 bummerls).

### Improvements in the imperfect information scenarios

I couldn't prove that the confidence gains from the Mcts algorithm (perfect
information) improve the confidence of the MctsPlayer (imperfect information).
I had two main issues:

* I didn't know how to compute the CI of the action score at the player level.
  Some attempts were made in `mcts_debug._average_ucb_with_ci`:
  * For each action consider only the scores coming from each permutation and
    compute the CIs of their mean. This doesn't take
    into account the CIs for these scores, so any improvement at the algorithm
    level cannot be seen at the player level (unless one action is supposed to
    have the similar score in all permutations?). This method is definitely not
    correct in the late stages of the game, where we can fully simulate the
    entire game tree for all permutations and there is no uncertainty in the
    score. 
  * Simple average of the CI limits coming from each permutation.
    (Q: Does this ignore the fact that we only look at a subset of permutations,
    and we don't process all possible permutations, so there should be some
    additional uncertainty on top of the uncertainty coming with each score?)
  * Use `scipy.stats.bootstrap` to get CIs on the averages computed at the
    previous bullet (most likely incorrect?!).
* The CI width for the best action doesn't seem to improve at the player level
  if we select the best child in each perfect information scenario. The ideas
  that I tried out were the following (since these use CIs, they also have the
  issues in the previous bullet points):
  * `mcts_permutations.py`: Manually debug the CI widths for a couple of game
    states as we increase the number of permutations processed ([link](https://github.com/cpatrasciuc/schnapsen-card-game/blob/66c2ecb/src/ai/eval/data/mcts_permutations_5000iter.png)). 
  * `mcts_variance_across_multiple_game_states`: For one game state, run the
    MctsPlayer *M* times and compute the standard deviation of each action score
    (as a measure of how much does the output change for the same input). Run
    this for *N* different game states and check if the mean standard deviation
    improves if we use UCB-based Selection.
  * `mcts_ci_widths_across_multiple_game_states`: Same as above, but instead of
    checking if the standard deviation shrinks, I checked whether the CI widths
    shrink after moving to UCB-based Selection.
  * `mcts_ci_widths_and_permutations_across_multiple_game_states`: For N game
    states, compute the average CI width of the action deemed best by the
    MctsPlayer and see how does this change as we increase `max_permutations`.
    There seems to be no significant difference between UCB-based Selection
    ([1000 iterations](https://github.com/cpatrasciuc/schnapsen-card-game/blob/73df21b89ca436c51a200530cbbfe76e7ee08435/src/ai/eval/data/mcts_ci_widths_and_perm_across_game_states_best_child_1000iter.png),
     [2500 iterations](https://github.com/cpatrasciuc/schnapsen-card-game/blob/73df21b89ca436c51a200530cbbfe76e7ee08435/src/ai/eval/data/mcts_ci_widths_and_perm_across_game_states_best_child_2500iter.png))
    and Random Selection
    ([1000 iterations](https://github.com/cpatrasciuc/schnapsen-card-game/blob/73df21b89ca436c51a200530cbbfe76e7ee08435/src/ai/eval/data/mcts_ci_widths_and_perm_across_game_states_random_1000iter.png),
     [2500 iterations](https://github.com/cpatrasciuc/schnapsen-card-game/blob/73df21b89ca436c51a200530cbbfe76e7ee08435/src/ai/eval/data/mcts_ci_widths_and_perm_across_game_states_random_2500iter.png)).
  * For *N* game states, run the MctsPlayer and count in how many cases there is
    an overlap between the CIs of the best and second-best action. This number
    improved a bit after switching to UCB-based Selection, but it wasn't
    convincing (it went from ~88% to ~75%).
  
**TODO:** 1) Find a proper way to compute CIs at the player level. 2) Maybe look
at the ratio between the final score and its CI width.

One possible explanation for why we don't see an improvement in the confidence
at the player level could be the following: when we select the best child, for
each perfect information scenario, we improve the confidence for the best
action's score, and we lose confidence for the scores of the other actions. Now,
unless some action is the best action across all perfect information scenarios,
we improve the confidence in its score in some scenarios, and we lose confidence
in its score in other scenarios. So at the player level (imperfect information
scenario), when we average across the perfect information scenarios, the changes
in confidence will cancel out. 

### Tuning the exploration parameter

Since I couldn't prove that switching to UCB-based Selection really improves
the MctsPlayer, I decided to create a set of players that use
`max_iterations=5000`, `max_permutations=20` and different values for the
exploration parameter in the equation above, let them play against each other
and check the results. I used the following values for the exploration
parameter: 0 (no exploration, just exploitation), 1/&radic;2, 1, &radic;2, 20,
5000 (for practical purposes, this high value should be equivalent to Random
Selection). The results are the following:

![exploration_param_eval_results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/ca0bbe9c7716b13c677bc0770a627882707776a7/src/ai/eval/data/eval_results_exploration_param.png)

### Conclusion

I will go forward with using UCB-based Selection with `exploration_param=1`.
This also matches the value recommended on [Wikipedia](https://en.wikipedia.org/wiki/Monte_Carlo_tree_search#Exploration_and_exploitation)
(note that the formula there is slightly different).

**NOTE**: In *"A Survey of Monte Carlo Tree Search Methods"* ([link1](https://ieeexplore.ieee.org/document/6145622), [link2](http://www.incompleteideas.net/609%20dropbox/other%20readings%20and%20resources/MCTS-survey.pdf))
the recommended value is &radic;2, if the rewards are in the interval [0, 1].
This is the other value that gave us good results, very similar to
`exploration_param=1`.

## Tune the max_iterations and max_permutations params

The purpose of this section is to find the best combination of `max_iterations`
and `max_permutations` for a fixed computational budget. I tried to pick two
budgets that would be similar to the initial setups, i.e., they would take 1
second and 5 seconds per move on my computer. Based on [this plot](https://github.com/cpatrasciuc/schnapsen-card-game/blob/80e0e15cfd95877df165da8a9a9f322ed2bf75a4/src/ai/eval/data/iterations_and_time_i7.png),
this corresponds to 100k and 500k iterations, respectively.

The work in this section lead to a couple of improvements that were developed in
parallel and then merged back into this work stream: adding UCB-based Selection
and allowing Computational Budget Reallocation.

### How does max_iterations influence the performance?

I tried to understand how does the number of iterations influence the
performance of the player. The initial hypothesis was that the performance will
increase if one uses a higher number of iterations. I tested this using a set of
players that process an equal number of permutations (30), but they use 1000,
2500, 5000 and 10000 iterations per permutation, respectively.

When using **Random Selection**, the players with more iterations were able to
defeat the ones with fewer iterations ([results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/62d05e61877044b89a60387ec65fbbc4c112e978/src/ai/eval/data/eval_results_same_perm_different_iterations.png)).
Everyone defeated the player that uses only 1000 iterations, and the player
using 10k iterations also defeated the one using 2500 iterations. By looking at
the [debug plots](https://github.com/cpatrasciuc/schnapsen-card-game/blob/4a7a996c36ab0986dadb411391f6b84c609daff3/src/ai/eval/data/mcts_iterations_40perm.png),
I didn't see a lot of changes in the order of the actions after 1000 iterations.
The relative order of the player's actions after 10k iterations seems to be very
similar to what we already have after 1k iterations, or even before that. One
exception might be the CloseTheTalon action which, given enough iterations,
might see significant changes in its score.

After switching to **UCB-based Selection**, the players with more iterations
could not beat the players with fewer iterations that often ([results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/c6278f07f1a44461f3d1b0488585df119462d4aa/src/ai/eval/data/eval_results_same_perm_different_iterations.png)).
This might suggest that the players are able to pick the good moves using fewer
iterations. This is in line with the [debug plots](https://github.com/cpatrasciuc/schnapsen-card-game/blob/f1f16624eda783efc6e45a246518299dff062247/src/ai/eval/data/mcts_iterations_40perm.png)
that show states where the best action is identified after a few iterations
and stays the best until the end (e.g., seed=0, seed=100 in the plots), as
opposed to Random Selection which doesn't settle on the best action that early.
Even the CloseTheTalon action it is explored earlier if it might be useful, or
discarded early otherwise.

After enabling **budget reallocation**, there is no clear conclusion on whether
more iterations lead to better performance ([results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/87fe5bab686730692ba6d3dcc7acfa26eba213d5/src/ai/eval/data/eval_results_same_perm_different_iterations.png)).
The [debug plots](https://github.com/cpatrasciuc/schnapsen-card-game/blob/fdf3b90e3a5560a719bac8bafe4ef78aa9eac9c9/src/ai/eval/data/mcts_iterations_100k_budget_with_reallocation.png)
also tell a similar story: the order of the action scores doesn't change
significantly for more iterations. It also doesn't change significantly when
compared to the [debug plots without budget reallocation](https://github.com/cpatrasciuc/schnapsen-card-game/blob/02db00ea2c311ff46ece595215d2f96cf64e0676/src/ai/eval/data/mcts_iterations_100k_budget_without_reallocation.png).

**NOTE:** The confidence on the plots above is a simple CI for the mean scores
coming from each permutation. That's why when using a smaller number of
iterations and constant budget, thus a larger number of permutations, the CIs
are tighter. If we don't pre-aggregate the rewards at permutation-level, and 
just feed all the rewards in a single big average across permutations, this
difference in confidence goes away ([plots](https://github.com/cpatrasciuc/schnapsen-card-game/blob/10cad087e86a92e7e466c70fb4e74113077a4a7d/src/ai/eval/data/mcts_permutations_100k_budget_with_reallocation_ci_on_raw_rewards.png)).
This is also affected by the issues I had with the CIs at player level,
described in the previous section.

### How does max_permutations influence the performance?

I tried to understand how does the number of permutations influence the
performance of the player. The initial hypothesis was that the performance will
increase if one uses a higher number of permutations. I tested this using a
set of players that run an equal number of iterations per permutation (2500),
but they process 1, 5, 10, 40, 80 and 150 permutations, respectively.

With **Random Selection**, it wasn't clear that more permutations lead to better
performance ([results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/be3350fcd54e59b39774d11cac4f9622891ed2cc/src/ai/eval/data/eval_results_same_iterations_different_permutations.png)).
It was expected that the players that use only 1 or 5 permutations will lose
against all the other players. I was surprised though that the players that use
40 or 80 permutations couldn't be significantly better than the player that uses
10 permutations in 1000 bummerls. The [debug plots](https://github.com/cpatrasciuc/schnapsen-card-game/blob/bef006f4ed8dd91b5e7e03a087eb9fc8e3c94b17/src/ai/eval/data/mcts_permutations_5000iter.png)
don't show any significant changes between 10 or 150 permutations. I had two
possible explanations: (1) the scores from each permutation are not accurate
enough, and/or (2) we need to process significantly more permutations, which
implies fewer iterations per permutation, so we need to make sure we use the
iterations wisely. Based on both these ideas, I decided to add support for
[UCB-based Selection](#select-the-best-child-and-balance-exploration-vs-exploitation).

After enabling **UCB-based Selection**, the players with more permutations were
able to beat the player that uses only 10 permutations ([results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/c6278f07f1a44461f3d1b0488585df119462d4aa/src/ai/eval/data/eval_results_same_iterations_different_permutations.png)).
The differences might not be significant though. On the [debug plots](https://github.com/cpatrasciuc/schnapsen-card-game/blob/4d37a7fc541a18ce23fff726f8748ef1075cc929/src/ai/eval/data/mcts_permutations_100k_budget_without_reallocation.png)
there is some noise when using less than 40 permutations, but then the order
of the actions is pretty stable, as before.

After enabling **budget reallocation**, the [results grid](https://github.com/cpatrasciuc/schnapsen-card-game/blob/0c91c063767e7c439e4f380707eea97213ba4ee7/src/ai/eval/data/eval_results_same_iterations_different_permutations.png)
and [debug plots](https://github.com/cpatrasciuc/schnapsen-card-game/blob/4d37a7fc541a18ce23fff726f8748ef1075cc929/src/ai/eval/data/mcts_permutations_100k_budget_with_reallocation.png)
showed no big changes.

#### Does it matter which permutations we process?

One reason for which increasing the number of permutations doesn't lead to a
significantly better player could be that the initial permutations that we
process are already giving us enough information to make a good decision. I
evaluated this using a set of players that use 150 permutations and 667
iterations per permutation, but each uses a different algorithm to generate the
permutations (for more details, see `permutations.py`):
* **Random**: Generates the permutations in a random order, excluding
  duplicates.
* **Lexicographic**: Generates the permutations in lexicographic order.
* **Sims-Tables**: Uses Sims-Tables to generate the permutations in an order 
 that maximizes *dispersion* (a metric that measures how different from each
 other are the permutations; see `dispersion()` in `permutations.py`). As
 opposed to the other two algorithms, this one also knows that the order of the
 cards in the opponent's hand doesn't matter.

The evaluation results show that the permutations we pick for processing can
influence the performance of the player:

![eval_permutations](https://github.com/cpatrasciuc/schnapsen-card-game/blob/49c48d3ef941969c90e71c4ae96b116a88bdd22f/src/ai/eval/data/eval_permutations.png)

As expected, when using permutations in lexicographic order we don't see enough
different scenarios to make good decisions, so this algorithm lost against both
Random permutations and Sims-Tables permutations. There was no clear difference
between Random and Sims-Tables. This is also expected, because for a small
number of permutations (150 in our case) the dispersion of the Random
permutations is similar to the one achieved using Sims-Tables (the X-axis in the
plots below represents the number of permutations requested out of ~726M
possible permutations at the beginning of a game).

![dispersion](https://github.com/cpatrasciuc/schnapsen-card-game/blob/88f57e77b36c253e7c39086b61b86ee2c096e281/src/ai/eval/data/permutations_dispersion.png)

For 150 permutations, the Random generator is faster than Sims-Tables:

![time](https://github.com/cpatrasciuc/schnapsen-card-game/blob/88f57e77b36c253e7c39086b61b86ee2c096e281/src/ai/eval/data/permutations_time.png)

Since we only spend ~0.7% of the time in Sims-Table permutations generator
([CPU profile](https://github.com/cpatrasciuc/schnapsen-card-game/blob/aced1310e03e704fee0ca4718df70c5240450d36/src/ai/eval/data/iterations_and_time_100perm.profile.txt)),
I prefer to continue using it, instead of relying on randomness to achieve high
dispersion. This algorithm was used in all the other evaluations described here. 

### Fixed computational budget grid

Since there was no clear conclusion on how to pick a good value for
`max_iterations` or `max_permutations`, I decided to generate a grid of players
with various combinations of max_iterations and max_permutations such that:
`max_iterations * max_permutations = 100k iterations`.

#### Reallocating the computational budget

After the initial games in this grid, the player using 10 permutations and
10k iterations was significantly better than the player using 40 permutations
and 2500 iterations ([results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/790f1aba3d7962ad358fd9347f7575b50104d797/src/ai/eval/data/eval_results_100k_iter_budget.png)).
It also won more than 50% of the bummerls against the player using 70
permutations and 1428 iterations. This was surprising, because in the grid
from the previous sub-section, where we use the same number of iterations (2500)
and different permutations, the player that uses 10 permutations was defeated by
all the other players ([results grid](https://github.com/cpatrasciuc/schnapsen-card-game/blob/0c91c063767e7c439e4f380707eea97213ba4ee7/src/ai/eval/data/eval_results_same_iterations_different_permutations.png)).
Given that after 4 out of 10 possible tricks, there are at most 6 permutations
to process, and after 5 tricks there is only one permutation (i.e., the game
becomes a perfect information game), the players that have `max_permutations >
6` have no advantage. On top of that, the lower values for max_iterations (since the total
budget must remain constant) might cost them the win in the late game.

I introduced `MctsPlayerOptions.reallocate_computational_budget` which allows
the players to increase the number of iterations per permutation late game,
such that the total computational budget stays the same. This means that:

*actual_permutations * actual_iterations = max_permutations * max_iterations*

I confirmed that this option is an improvement by itself, by simulating 100
bummerls between two players that use the same options (max_permutations=150,
max_iterations=667), except that one reallocates the budget and the other one
doesn't (`MctsPlayerReallocateBudget` and `MctsPlayerDoNotReallocateBudget` from
`players.py`). The player that reallocates the budget won in **64% [54.24%, 
72.73%]** of the cases.

By enabling this option for all the players in the grid, there is no difference
between them after the forth trick, and the only differences in performance
should come from the first 4 tricks (where processing more permutations should
be better). This was indeed the case: after allowing players to reallocate the
budget late game, the player that uses 10 permutations and 10k iterations was
defeated by the other two players ([results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/64b75c2981f8100ec97700e7573af10b14da2e64/src/ai/eval/data/eval_results_100k_iter_budget.png)).

#### Can we make sure we fully simulate closing the talon?

Closing the talon could be a powerful action: if you think you are in a position
to win the game, you can win it faster and get more game points since the score
is based on your opponent's trick points at the time the talon gets closed. If
there is no clear difference in how we pick max_permutations and max_iterations,
one idea could be to pick a value for max_iterations such that the player can
fully simulate that subtree within the budget, and make better decisions on when
it should close the talon. The player can still choose to close the talon even
if the subtree is not fully simulated, but it will do so based on the UCB score
not based on the MiniMax score.

To investigate this, I took 1000 random game states (seed between 0 and 999) and
run on each of them 10k iterations of the Mcts algorithm. After 10k iterations,
if the CloseTheTalon action is not fully simulated it means the algorithm didn't
consider it useful enough and spent the budget on other actions. Since closing
the talon is not very relevant in these scenarios, I excluded them from the
analysis. For the remaining game states I looked at how many iterations were
required until CloseTheTalon action was fully simulated. I then repeated the
same analysis, on the same game states, but after 1, 2, 3 or 4 random tricks are
played. The code for this is in `iterations_for_closing_the_talon.py`.

The percentiles for the number of iterations required to fully simulate
the CloseTheTalon action are as follows:

| Scenario | Fully simulated scenarios | Min | 25% | 50% | 75% | Max |
| :------: | :-----------------: | :---: | :---: | :---: | :---: | :---: |
| Start of the game | 4% | 600 | 1200 | 2000 | 4850 | 9700 |
| After 1 trick | 11% | 300 | 1000 | 2000 | 4700 | 9000 |
| After 2 tricks | 21% | 100 | 800 | 1450 | 3976 | 10000 |
| After 3 tricks | 34% | 52 | 600 | 1400 | 4076 | 9900 |
| After 4 tricks | 62% | 38 | 500 | 1600 | 4400 | 10000 |  
 
Observations based on the numbers above:
* As we advance through the game, closing the talon becomes more and more
  important. At the beginning of a game we fully simulate this action only in 4%
  of the cases; after 4 tricks we fully simulate it in 62% of the cases. As the
  action becomes more and more important, the Mcts algorithm also expands it
  earlier (25th percentile goes from 1200 iterations at the beginning of a game
  to 500 iterations after 4 tricks).
* There is no big change in the 50th and 75th percentile as we advance through
  the game, which probably means these are the cases where it's not that obvious
  whether closing the talon is the best action, and it stays so.
* After 4 tricks there are at most 6 permutations possible, so with a 100k total
  computational budget, a player would use 100k / 6 = 16k iterations. This means
  that it will cover all the 62% of the cases from the last row in the table,
  and maybe a few more from the 38% that were not fully simulated within 10k
  iterations.
* After 3 tricks, the player can cover the 25th percentile if it uses less than
  100k / 600 = 166 permutations.
* After 2 tricks, the player can cover the 25th percentile if it uses less than
  100k / 800 = 125 permutations.
* Trying to cover early game scenarios is probably not worth it. If we only
  consider the 25th percentile as scenarios where closing the talon is a viable
  option, this only happens in 25% of 4% = 1% of the initial game states. On top
  of that, this is only one permutation, and for CloseTheTalon to be the best
  action, it would have to be the best action in a lot of other permutations.

### Conclusion

The final grid for a total budget of 100k iterations can be seen [here](https://github.com/cpatrasciuc/schnapsen-card-game/blob/f1ddf49aa0a6d16523d19644bf51782438683dca/src/ai/eval/data/eval_results_100k_iter_budget.png).
There was no clear winner, so I looked at other metrics, such as game points won
and trick points won. It seems that the players having 130 and 160 permutations
are slightly better than the others on these metrics, so I decided to pick a 
value between these two. I will move forward with a player that uses 150
permutations and 667 iterations per permutation.

For the 500k-iterations budget, I used the 100k iterations player as a starting
point and generated a grid of three players: for one I multiplied max_iterations
by 5, for one I multiplied max_permutations by 5, and for one I multiplied both
max_iterations and max_permutations by &radic;5. No player was significantly
better than any other player over 1000 bummerls in any metric
([grid results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/f71f59033c8637314e334f0e05f7e89bad7907c2/src/ai/eval/data/eval_results_500k_iter_budget.png)).
I will go forward with the player that increases both max_iteration and
max_permutations.

## Start with the action deemed best by the HeuristicPlayer

In this section, I experimented with the following idea: when we expand a node
in the Mcts tree for the first time, instead of choosing an action randomly, use
the action deemed best by the HeuristicPlayer for that game state. I wanted to
see if that would help find the best child of a node using fewer iterations
and then exploit that using UCB-based selection. 

Since the CythonMctsPlayer uses C/C++ and the HeuristicPlayer uses Python, there
is no easy way to make them work together. I'd have to rewrite the
HeuristicPlayer from scratch in Cython. Before investing any effort in this, I
wanted to check if it's worth it, so I implemented a prototype that stores in
each node both the C and the Python game states. These code changes are in the
`cython_with_heuristic` branch. Because there is a lot of back-and-forth between
C/C++ (no GIL) and Python (GIL) code, this prototype is 100x slower. I could
simulate only 100 bummerls between two players that both use
max_permutations=150 and max_iterations=667, but one uses the HeuristicPlayer
and the other one doesn't. Both players won exactly 50 out of 100 bummerls, with
no significant difference in any of the other metrics:

```
Simulating MctsPlayerDoNotUseHeuristic vs MctsPlayerUseHeuristic
bummerls: 50:50
games: 296:308
game_points: 520:523
trick_points: 31517:31542
perf_counter_sum: 1025.7731822589913:110927.6047436561
process_time_sum: 1025.6098739998947:110905.88797799998
num_actions_requested: 4125:4104
Duration (time): 8:21:04.775068
```

As an additional data point, I run the MctsPlayer over 1000 initial game states
and for each node in the resulting Mcts tree, I identified the action deemed
best by the HeuristicPlayer, and then I checked where it ranked among the other
actions based on the number of visits. A rank of 0 means that the action deemed
best by the HeuristicPlayer was also considered the best one by the Mcts
algorithm, and thus it got visited the most. The code for this is in
`overlap_between_mcts_and_heuristic.py`. I was not looking for a specific
distribution, I just wanted to compare the results between using and not using
the HeuristicPlayer with UCB-based Selection. In particular, there is no goal to
maximize the number of cases where rank is 0, because that means we are either
playing exactly like the HeuristicPlayer (but we want MctsPlayer to be
better) or we are visiting all the children equally (i.e., Random Selection).

In the plots below, there is no difference between using or not using the
HeuristicPlayer with UCB-based Selection. This suggests that it doesn't matter
what action we process first; we will probably reach a similar result in the
end.

| ![random](https://github.com/cpatrasciuc/schnapsen-card-game/blob/5af671138883576ee3df25dd0c8bbae77539323b/src/ai/eval/data/overlap_between_mcts_and_heuristic_random.png) | ![ucb](https://github.com/cpatrasciuc/schnapsen-card-game/blob/5af671138883576ee3df25dd0c8bbae77539323b/src/ai/eval/data/overlap_between_mcts_and_heuristic_ucb.png) | ![ucb_with_heuristic](https://github.com/cpatrasciuc/schnapsen-card-game/blob/aeb80fcb3c043324feffd594e939af34d89c0938/src/ai/eval/data/overlap_between_mcts_and_heuristic_ucb_with_heuristic.png) |
| :---------: | :------: | :---------------------: |

Since the first action we select when we visit a node for the first time
doesn't seem to influence the performance of the MctsPlayer, I will not pursue
this idea further.  

## Improve the aggregation of scores from all Mcts trees

The MctsPlayer converts an imperfect information game to a list of perfect
information games (based on the `max_permutations` param), then it runs the Mcts
algorithm on each perfect information game, resulting in a list of Mcts trees.
In order to decide which action is the best one, the player needs to aggregate
for each action the scores that this action has in all the Mcts trees. In this
section I evaluated different solutions for aggregating the scores:
* **MostFrequentBestAction**: In each tree we look for the action having the
  highest score and consider it the best action for that tree. The final
  aggregated score for one action is the number of trees for which the action is
  the best action.
* **AverageUcb**: The aggregated score for one action is the arithmetic mean of
  the individual scores from all trees. If the subtree corresponding to this
  action in one of the trees is fully simulated, we use the minimax score from
  this tree.
* **CountVisits**: The aggregated score for one action is the total number of
  visits that this action got in all the trees. This only makes sense if
  UCB-based Selection is used, so the best nodes in each tree get more visits.
* **SimpleAverage**: The aggregated score for one action is `sum(Qi) / sum(Ni)`,
  where `Qi` is the total reward that this action got in the i-th tree, and `Ni`
  is the number of visits that this action got in the i-th tree. If the subtree
  corresponding to this action in one of the trees is fully simulated, `Qi` is
  the minimax score from this tree multiplied with the number of visits.
* **WeightedAverage**: The aggregated score for one action is `sum(Qi * Ni) /
  sum(Ni)`. `Qi` and `Ni` have the same meaning as for SimpleAverage.
* **LowerCiBoundAverage**: The aggregated score for one action is the lower CI
  bound of the arithmetic mean of the scores from all trees. The CIs are
  computed using `scipy.stats.bootstrap`.
* **LowerCiBoundOnRawRewards**: The aggregated score for one action is the lower
  CI bound of the arithmetic mean of all the raw rewards on all the paths going
  through this action from all the Mcts trees. If UCB-based Selection is used,
  there will be more paths going through an action in the trees where this
  action leads to better results. This means that in the final aggregation we
  will get more entries from the scenarios where an action is good and fewer
  entries from the scenarios where the action is bad. It's probably better to
  use RandomSelection if we don't want to bias the final score.

In order to find out which of these possible solutions is the best, I run a grid
with a set of players that use the same settings (max_permutations=150 and
max_iterations=667), but different score aggregation functions:

![eval_merge_scoring_info_func.png](https://github.com/cpatrasciuc/schnapsen-card-game/blob/875152a4f60f9de3c2feaed10d3e03e1dcb9cf30/src/ai/eval/data/eval_merge_scoring_info_func.png).

The player that uses **AverageUcb** was significantly better than all the other
players, except **LowerCiBoundAverage**. LowerCiBoundAverage introduces a
dependency to scipy and uses more CPU to do the bootstrap resampling, without
improving the performance of the player (measured using 1000 bummerls).

In conclusion, I will move forward with using **AverageUcb** as the score
aggregation function.

## Reuse the nodes from previous decisions

When the MctsPlayer makes a decision, it simulates a significant number of
games until completion, then it picks the action that had the best overall
outcome and plays it. It then discards all the scenarios it simulated, so the
next time it has to make a move, it starts from scratch using the new game
state at that moment. The idea to experiment with in this section is to cache
the game states that were already seen in previous decisions and see if reusing
this data can improve the player.

When we expand a tree node, and we reach a new game state, we would have to
search for this game state in a cache that would map the already seen game
states to the corresponding tree nodes. If there is already a node for this game
state, we would reuse it, instead of creating a new one.
Unfortunately, implementing this idea is not trivial for the following reasons:
* **Graph/DAG**: If we always reuse a game state/node from the cache, it means
  that one game state might have multiple parent states, so the Mcts trees will
  become a directed acyclic graph (DAG). This means that the backpropagation of
  the rewards from the leaves back to the root must be updated accordingly.
* **Speed**: Every time we visit a game state we would have to first
  search for it in the cache: compute the hash, look up the hash in the cache,
  compare the game states from the cache with our game state. This might be too
  slow.
* **Cache size**: For a budget of 100k iterations we are visiting around 1M
  different game states per decision in the early game stages. The size of the
  cache might grow rapidly and become a concern.
* **Cache cleanup**: If we want to remove entries from the cache, figuring out
  which entries should be deleted and which ones should be kept, might take a
  significant amount of time. 
* **Libraries**: If we want to be fast, we would use a hash map for the cache.
  If we do it in Python, it would slow everything down significantly
  because of the back-and-forth between C/C++ (no GIL) and Python (GIL) code.
  Doing it in C++ with STL might be tricky because we would have to implement
  `std::hash` for our Cython struct (it's most likely not possible, but I didn't
  study it in depth). Writing our own hash map in C or Cython requires more
  work.

Before tackling these non-trivial problems I did a quick prototype in Python.
The code for it is in the `node_cache` branch. Using this prototype I measured
how many cache calls we would do and how many cache hits we would get, by
playing 100 bummerls between MctsPlayer and HeuristicPlayer. Every time the
MctsPlayer is asked to make a decision, I considered that a new *step*. When
I get a cache hit, I'm also storing the step at which the cache entry was added
to the cache. The results are the following:

![cache_stats](https://github.com/cpatrasciuc/schnapsen-card-game/blob/0e8743cf3e99de021dcfdf7089f9443baeb37356/src/ai/eval/data/cache_stats_100_bummerls_vs_heuristic.png)

Takeaways:
* At the 5th step and later (i.e., approximately after four tricks are played),
  the number of cache calls is very low, because we don't have to visit a lot of
  game states at the end of the game. We most likely can fully simulate the
  entire game tree at this stage and a cache won't bring any performance benefit
  (i.e., the player will not make better decisions).
* In the first 3 steps we get 81% or more cache misses, so it seems a cache
  would not help in these situations either.
* In the 4th step, we get 52% cache hits. Two thirds of the hits are game states
  that were added to the cache also in step 4 (so we reach them multiple times
  through different paths that are explored only in step 4). This 4th step might
  be the only scenario where a cache might help.

If we cache the game states from previous decisions, how would we use this
information? There are two possible ways:
* Some entries from the cache might be valid given the current game situation,
  but would not match the specific permutations we process at the current step
  (i.e., at step *i*, we consider that the opponent might have cards *C* in
  their hand, the opponent might still have cards *C* in their hand at step
  *i+1*, but we decided to process other permutations at this step, where the
  opponent has other cards in their hand). In this case, we could reuse the info
  from the cache as if it were a new permutation in addition to the ones we
  process at the current step.
* If the entries in the cache match the permutation we process at the current
  step we continue expanding that subtree. This means reusing the data from the
  cache saves us some iterations.

Since reusing the data from the cache is equivalent to having more iterations
and/or more permutations, I tried to estimate if this would improve the
performance of the MctsPlayer by simulating 1000 bummerls between the
100k-iterations-budget player (max_permutations=150, max_iterations=667) and the
500k-iterations-budget player (max_permutations=335, max_iterations=1491).
The player with the higher budget was not significantly better:

```
Simulating MctsPlayerAverageUcb vs MctsPlayerIterAndPermXSqrt5
bummerls: 478:522 47.80% [44.72%, 50.90%]
games: 2964:3098 48.89% [47.64%, 50.15%]
game_points: 5182:5376 
trick_points: 316279:319600
```

It is not clear that adding a cache would improve the MctsPlayer, or that the
improvement would outweigh the work required to implement it. As a result,
I will not pursue this further in this version of the player.   

## Use Information Set Monte Carlo Tree Search

In this section I experimented with using *Information Set Monte Carlo Tree
Search (IS-MCTS)*. In IS-MCTS, we use a single tree. At the top of the tree we
have a level of imperfect information nodes for each possible action in the
current game state (I called them *action nodes*). We also use a list of
*N* permutations. Each action node has *N* perfect information children,
obtained by playing that particular action in the game state corresponding to
each of the *N* permutations. In each IS-MCTS iteration, we
first pick an action node using UCB-based selection, then we pick one of its
perfect information children randomly, and we run a normal Mcts iteration
starting from this node. At the end of the iteration, we also update the
action node stats based on the information back-propagated from the new leaf.

The possible improvements over the MctsPlayer are:

* We could identify bad actions earlier, instead of having to identify them *N*
  times, once in each permutation. This could reduce the total number of
  iterations spent on bad actions.
* We should also spend fewer iterations on actions that are good only in a
  couple of permutations, but bad overall.
* We might know earlier which action is good across all permutations and invest
  more iterations in it, as opposed to identifying this action only at the end
  in the MctsPlayer, after the scores from all the permutations are aggregated.
    

To evaluate this, I've run the best MctsPlayer so far for the 100k-iterations
budget against two IS-MCTS players, both having a total computational budget of
100k iterations as well, one using 150 permutations and the other 10000
permutations. Note that the MctsPlayer cannot use 10000 permutations because
that would imply only 10 iterations per permutation for a total budget of 100k
iterations. I wanted to see if using a high number of permutations and letting
the IS-MCTS player decide where to spend the whole budget can improve the
overall performance of the player.

Unfortunately, none of the IS-MCTS players was significantly better than the
MctsPlayer over 1000 bummerls.     

TODO: eval an is mcts player that uses sum(q)/sum(n) in action nodes.

| IS-MCTS Config | Win rate against MctsPlayer(max_permutations=150, max_iterations=100) |
| :------------: | :-------------------------------------------------------------------: |
| 150 permutations | 48.40% [45.31%, 51.50%] |
| 10000 permutations | 50.10% [47.01%, 53.19%] |

Since switching to IS-MCTS would require all the debug tools to be updated, I
decided not to use this in this version of the MctsPlayer.

Notes:
* When the IS-MCTS player uses a high number of permutations (e.g., 10k) the
  permutations' generation part starts to take a significant amount of time.
  Some optimizations might be necessary if we decide to use this in the future.
* The code for this experiment is in the `is_mcts` branch.

## Tiebreakers

TODO

## Final results

TODO(final eval):
- Check correlation between game points won and initial cards or diff between
  initial cards
- Check the correlation above for Mcts vs Mcts and Mcts vs Heuristic 