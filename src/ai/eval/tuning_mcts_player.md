# Tuning MctsPlayer

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

**TODO:** Verify this computations by rerunning and logging the number of iterations.

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
- [ ] When a node is expanded for the first time, start with the action deemed best by the HeuristicPlayer
- [ ] Maybe reuse the nodes from the previous decisions instead of always starting from scratch
- [ ] Improve merging the scores across root nodes
- [ ] Expand an action and a permutation in each iteration

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
measured its speed in `GameStateCopyTest`. The results as follows:

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
[reuse these nodes/trees](#reuse-nodes-from-previous-decisions) later. 

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

TODO

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

By using this, there is no difference between the players in the grid after the
forth trick, and the only differences in performance should come from the first
4 tricks (where processing more permutations should be better). This was indeed
the case: after allowing players to reallocate the budget late game, the player
that uses 10 permutations and 10k iterations was defeated by the other two
players ([results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/64b75c2981f8100ec97700e7573af10b14da2e64/src/ai/eval/data/eval_results_100k_iter_budget.png)).

TODO: Evaluation of the reallocation option.

### Conclusion

The final grid for a total budget of 100k iterations can be seen [here](https://github.com/cpatrasciuc/schnapsen-card-game/blob/f1ddf49aa0a6d16523d19644bf51782438683dca/src/ai/eval/data/eval_results_100k_iter_budget.png).
There was no clear winner, so I looked at other metrics, such as game points won
and trick points won. It seems that the players having 130 and 160 permutations
are slightly better than the others on these metrics, so I decided to pick a 
value between these two. I will move forward with a player that uses 150
permutations and 667 iterations per permutation.

TODO: Tune max_iterations and max_permutations for a budget of 500k iterations.

TODO Idea: 
If evals are equal, consider picking max_iterations such that at least we can fully simulate
the CloseTheTalon action. Run 100 game states, max_iterations=10000, filter out
the cases when the action was not fully simulated, see how many iterations were
needed for the other cases. 

## Start with the action deemed best by the HeuristicPlayer

TODO

## Reuse nodes from previous decisions

TODO

## Improve root_node merging

TODO
