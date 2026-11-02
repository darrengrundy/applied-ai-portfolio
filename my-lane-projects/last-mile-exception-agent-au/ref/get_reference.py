"""Download the public Australian postcode table (locality coordinates, SA4 regions).

  ref/pc.csv - github.com/matthewproctor/australianpostcodes
"""
import os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PC = "https://raw.githubusercontent.com/matthewproctor/australianpostcodes/master/australian_postcodes.csv"

if __name__ == "__main__":
    urllib.request.urlretrieve(PC, os.path.join(HERE, "pc.csv"))
    print("ref/pc.csv ready")
