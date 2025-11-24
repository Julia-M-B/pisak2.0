from pisak.predictions.prepare_words_set import get_words_set
import random
import os

# Get the directory where this file is located
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(CURRENT_DIR, "lorem_ipsum.txt")
N_WORDS = 10

available_words = get_words_set(FILE_PATH)


