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
