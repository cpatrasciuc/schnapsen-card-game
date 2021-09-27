# Tuning MctsPlayer

## The problem

The initial version of the MctsPlayer lost 70 out of 100 bummerls against
the HeuristicPlayer. After switching from `most_frequent_best_action` to
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
- [ ] Find the best combination of max_iterations and max_permutations for a fixed computational budget
- [x] Pick the best child during the selection phase and balance exploration versus exploitation
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

## Tune the max_iterations and max_permutations params

It seems the permutations stabilize after 30-40 permutation. For iterations it's
not that clear. I will fix the total_iterations budget and permutations;
max_iterations will be budget / max_permutations.

For total_time ~ 1 sec:
Total iterations budget: ~100k iterations
Combinations to try out: 
- 10 perms, 10k iterations
- 30 perms, 3333 iterations
- 50 perms, 2000 iterations
Starting with 100 bummerls, no significant difference and each player won once and lost once.

Spreading a bit the number of permutations:
- 10 perms, 10k iterations
- 40 perms, 2500 iterations
- 70 perms, 1428 iterations
Using 100 bummerls, no significant difference. 10 perm has won against both, 70 has lost against both.
Update #1, after switching to UCB-based Selection:
Using 1000 bummerls, 10perm has won against 40perm, the other were neutral.
I was surprised that low perm high iter wins, given that after the switch to UCB-based Selection perms importance increased and iter importance decreased.
I assumed that after 4 tricks, when there are only 6 perms at most, the high iter can simulate more and win the late game.
Update #2:
I allowed the high-perm-low-iter players to reallocate the budget in the late game.
The high perm players now win against the 10perm-10000iter.
Next step: Go even higher with the number of perm: 100perm,1000iter.

Try out the hypothesis: for a fixed num of permutations 30, the more iterations the better.
- 30 perm, 10000 iter
- 30 perm, 5000 iter
- 30 perm, 2500 iter
- 30 perm, 1000 iter
- Conclusion: it seems to be true, but the differences are smaller after UCB-based Selection.

Try out the hypothesis: for a fixed num of iterations, the more permutations the better.
- 10 perm, 2500 iter
- 40 perm, 2500 iter
- 80 perm, 2500 iter
- 150 perm, 2500 iter
- Conclusion: it seems to be true, and the effect of increasing max_permutations increased after we switched to UCB-based Selection.


For total_time ~ 5 sec:
Total iterations budget: ~500k iterations
Combinations to try out:
- 10 perms, 50k iterations
- 30 perms, 16666 iterations
- 50 perms, 10000 iterations

Idea: 
If evals are equal, consider picking max_iterations such that at least we can fully simulate
the CloseTheTalon action. Run 100 game states, max_iterations=10000, filter out
the cases when the action was not fully simulated, see how many iterations were
needed for the other cases. 

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
  Some attempts were made in `mcts_debug._max_average_ucb_with_ci`:
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

## Start with the action deemed best by the HeuristicPlayer

TODO

## Reuse nodes from previous decisions

TODO

## Improve root_node merging

TODO
