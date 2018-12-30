# mtg\_deck\_compiler

Compile batches of card images

# Dependencies

* ImageMagick  
* [python-requests](http://python-requests.org)  
* fpdf  

Install python packages:
```
pip install -r requirements.txt
```

# Usage
```
./mtg_deck_compiler.py [-h] [-p PREFIX] [-c CACHE] [-f FORMAT] [-m MERGE] [-k] [-o] deck_file
```

Example (generate a single pdf):  
```
./mtg_deck_compiler.py deck.txt -m deck.pdf -c ~/.mtg_deck_compiler/cache
```

Example deck file:  
```
4 Plains  
3 Gideon, Ally of Zendikar
```
