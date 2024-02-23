import random
import string


class RandomDataGen:
    def __init__(self):
        self.random_string_length = 6
        self.characters = string.ascii_uppercase
        self.double_distribution = (1, 100.0)
        self.int64_distribution = (1, 100)
        self.bool_distribution = (0, 1)

    def get_random_string(self):
        random_string = ''.join(random.choice(self.characters) for _ in range(self.random_string_length))
        return random_string

    def get_random_float(self):
        return random.uniform(*self.double_distribution)

    def get_random_double(self):
        return random.uniform(*self.double_distribution)

    @staticmethod
    def get_random_int32():
        RandomDataGen.int32_value += 1
        return RandomDataGen.int32_value

    def get_random_int64(self):
        return random.randint(*self.int64_distribution)

    def get_random_bool(self):
        return random.choice([True, False])

    # Initialize the class variable
    int32_value = 1

