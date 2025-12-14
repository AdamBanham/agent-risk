# Helpful debuggin commands

In order to find the number of failures within a run set
use the folllwing command, within the eval folder:

```bash
grep -r --color -C 3 "Engine 'AI Engine' failed" | grep -o --color "'player': [0-8]" | sort | uniq -c
```

Returns:

```bash
  count | player
      2 'player': 0
     14 'player': 1
   4912 'player': 3
      8 'player': 4
      6 'player': 5
    583 'player': 6
```

To get an understanding of the types of errors occuring, use
the following command:

```bash
grep -or --color ".*Error:" | grep -o --color ":.*Error:" | sort | uniq -c
```

Returns:

```bash
  count | error 
    5482 :IndexError:
    3 :TypeError:
    1 :UnboundLocalError:
    1 :ValueError:
    20 :ZeroDivisionError:
```

To check:

combo_0530.stack-    plan = planner.construct_plan(game_state)
combo_0530.stack-  File "F:\Projects\agent-risk\risk\agents\mcts\defensive\attack.py", line 179, in construct_plan
combo_0530.stack-    action, reward = mcts.search(mcts_state, need_details=True)
combo_0530.stack-                     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
combo_0530.stack-  File "C:\Users\adam\.virtualenvs\agent-risk-TREN8mHm\Lib\site-packages\mcts\searcher\mcts.py", line 150, in search
combo_0530.stack-    best_child = self.get_best_child(self.root, 0)
combo_0530.stack-  File "C:\Users\adam\.virtualenvs\agent-risk-TREN8mHm\Lib\site-packages\mcts\searcher\mcts.py", line 266, in get_best_child
combo_0530.stack-    return random.choice(best_nodes)
combo_0530.stack-           ~~~~~~~~~~~~~^^^^^^^^^^^^
combo_0530.stack-  File "C:\Program Files\Python313\Lib\random.py", line 351, in choice
combo_0530.stack:    raise IndexError('Cannot choose from an empty sequence')
combo_0530.stack:IndexError: Cannot choose from an empty sequence

    744 :IndexError:
      1 :ValueError:

    744 'player': 3
      2 'player': 4