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
MCTS iterations for a perfect information scenario.

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

- [ ] Reduce CPU usage, so we can run more iterations within the budget
- [ ] Find the best combination of max_iterations and max_permutations for a fixed computational budget
- [ ] Pick the best child during the selection phase and balance exploration versus exploitation
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
> MCTS algorithm is allowed to perform before it must pick a move 
> ([commit](https://github.com/cpatrasciuc/schnapsen-card-game/commit/d267004c089d9d2ba15d4ed6d96de0b98b3d33ca)).
> This makes the performance of the MctsPlayer comparable across different runs, even
> across different machines.

## Reduce CPU usage

I added CPU profiling to [`iterations_and_time.py`](https://github.com/cpatrasciuc/schnapsen-card-game/blob/main/src/ai/eval/mcts_iterations_and_time.py).
The [first results](https://github.com/cpatrasciuc/schnapsen-card-game/blob/e19317e77cf9533f813ae651b2d996f153074e4b/src/ai/eval/data/iterations_and_time.profile.txt)
showed that 88% of the time is spent in `copy.deepcopy()`.

#### Step 1: Replace copy.deepcopy() with GameState.deep_copy()

I added my own `GameState.deep_copy()`, to create a deep copy of itself. I
measured its speed in `GameStateCopyTest`. The results as follows:

| Function | Time (ms) |
| :------: | :--------: |
| `copy.copy(game_state)` | 0.0030352 |
| `game_state.deep_copy()` | 0.0291062 |
| `pickle.loads(pickle.dumps(game_state))` | 0.0806335 |
| `copy.deepcopy(game_state)` | 0.3028298 |

Overall, this change allows the Mcts algorithm to run ~2x more iterations in the
same amount of time. However, [the new CPU profile](https://github.com/cpatrasciuc/schnapsen-card-game/blob/95eacb321110269495dbee47d5a8f185acb66c04/src/ai/eval/data/iterations_and_time.profile.txt)
shows that the new `GameState.deep_copy()` method takes ~66% of the time.

#### Step 2: Replace deep copies with shallow copies

Instead of making deep copies for the game states to be stored in each tree
node, I modified `PlayerAction.execute()` to create a (shallow) copy of the
input/parent game state that shares as many fields as possible with it
([commit](https://github.com/cpatrasciuc/schnapsen-card-game/commit/f263b24c8b7ab8c66b3a0ed8cd4b167d4579ed8)).

Overall, this change allows the Mcts algorithm to run ~2x more iterations in the
same amount of time. The amount of time spent in copying the game state and
executing a player action decreased from 73% (GameState.deep_copy: 66%,
PlayerAction.execute: 7%) to 26% (only PlayerAction.execute).

#### Step 3: multiprocessing.Pool overhead

Even if I managed to reduce the CPU usage of the Mcts algorithm (i.e., the
single threaded construction of one tree for a perfect information game state),
it was surprisingly slow in the `SchnapsenApp` for `max_iterations=1000-2000`
and `max_permutations=8-16`.

I measured how much time it takes the MctsPlayer to run a given number of
iterations. It seems that the `multiprocessing.Pool` overhead takes a
significant amount of time, most likely serializing and deserializing the data
between the parent and child processes. The Mcts algorithm is able to run 10k
iterations in ~10 seconds, but when the MctsPlayer runs 8 such algorithms in
parallel using `multiprocessing.Pool` it can only run ~2k iterations in the same
amount of time.

![iterations_and_time_8perm.png](https://github.com/cpatrasciuc/schnapsen-card-game/blob/main/src/ai/eval/data/iterations_and_time_8perm.png)

I experimented with the following ideas hoping they would reduce this overhead,
but none of them was successful:

* Implement my own MctsWorker and MctsWorkerPool (see the `mcts_worker` branch).
  This is similar to the `multiprocessing.Pool` but instead of using a
  single task queue, I split the permutations and directly assign
  them to specific child processes for processing. I tried using both `Pipe` and
  `Queue` to communicate with the children.
* Use the `dill` and `pathos` modules to see if they speed up the pickling.
* Use `ray`. It didn't work out of the box with `venv`. I did not debug further.
* Use `multiprocessing.dummy` just to make sure that threads don't work either.

TODO: Write this component in Cython and use threads.

## Tune the max_iterations and max_permutations params

TODO

## Select the best child and balance exploration vs exploitation

TODO

## Start with the action deemed best by the HeuristicPlayer

TODO

## Reuse nodes from previous decisions

TODO

## Improve root_node merging

TODO
