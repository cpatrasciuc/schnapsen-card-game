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

## Reduce CPU usage

TODO

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
