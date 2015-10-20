# Python Class Definitions

## A sample refactor of the final project ConferenceCentral_Complete.

### Preamble
The file conference.py contains the class definition
```python
class ConferenceApi(remote.Service):
    """Conference API v0.1"""
```
It stands at about 554 lines of code.

### Question
Can this class definition be split into multiple independent files ?

### Steps completed
1. Create folder named <b>conference</b>
2. Create file ```__init__.py``` inside folder <b>conference</b>
3. Split ```conference.py``` into three somewhat arbritary sections:
  1. Constants - ```const.py```
  2. Allocate Approx half of the functions into ```a.py```
  3. Allocate other half of the functions into ```b.py``` 
  4. What remains goes into ```__init__.py``` including Main Class Definition
4. Delete ```conference.py```

<hr>

#### Sources for reference
- http://stackoverflow.com/questions/9638446/is-there-any-python-equivalent-to-partial-classes
- https://docs.python.org/2/tutorial/modules.html

#### Original Code
https://github.com/udacity/ud858