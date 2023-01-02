import random

def generate_beeps():
    seg = random.randint(1, 6)
    phrases = []

    letters = ["e", "o", "i"]
    done_long = False

    for _ in range(0, seg):
        # pick mid letter
        letter = letters[random.randint(0, len(letters)-1)]
        chars = ["b"]

        # special case for certain letters
        if letter == "i":
            chars.append(letter)
        else:
            # a single random chance to generate long beep/boop
            b_num = 2
            if not done_long:
                b_num = random.randint(2, 4)
                if b_num > 2:
                    done_long = True
            for _ in range(0, b_num):
                chars.append(letter)

        chars.append("p")
        phrases.append("".join(chars))
    return " ".join(phrases)
