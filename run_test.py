choices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'a', 'b', 'c', 'd', 'e', 'f']

limit = 16
count = 0
for choice_a in choices:
    for choice_b in choices:
        if count % limit == 0:
            r = "{}{}".format(choice_a, choice_b)
            print("#{}".format(r*3))
        count += 1