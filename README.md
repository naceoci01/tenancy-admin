# Integration01 tenancy-admin
Scripts for maintaining orasenatdintegration01 tenancy

## Super-delete
Lorem ipsem...

## Policy Analysis
This script will run using instance principals and pull a recursive policy list, the nparse every statement into 4 categories:
* Special (define / endorse / etc)
* Service (allow service xxx)
* Dynamic Group (allow dynamic-group yyy)
* Regular (everything else)

Run this with:
```bash
foo
```

Once loaded into memory, the script allows for filtering.

Also with `-w` it will output JSON of what is in memory (filtered) so that it can be looked at later or in another tool.

### Filtering Commands

TBD

## Find Unused Dynamic Groups
Companion to policy script.  Uses the cached policy statements and loads all DGs from the tenancy into memory.  Once loaded, it checks to see if there are any DG policy statements that are applicable.  If not, it adds to a list (no deletes).

Run this with:
```bash
foo
```

