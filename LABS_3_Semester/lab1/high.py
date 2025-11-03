import sys
import math
import quodr

def get_coefs():
    coefficients = []
    for arg in sys.argv[1:]:
        try:
            coefficients.append(float(arg))
        except ValueError:
            print(f"Ошибка: '{arg}' не является числом")
            sys.exit(1)

    return coefficients

def decomposition(divisor, coefs):
    result = coefs.copy()
    for i in range(1, len(result)):
        result[i] = divisor * result[i - 1] + result[i]
    return result

def get_roots(coefs):
    roots = []
    current_coefs = coefs.copy()

    while len(current_coefs) > 1:
        if len(current_coefs) == 2:
            a, b = current_coefs
            if a != 0:
                root = -b / a
                roots.append(root)
            break

        last = current_coefs[-1]
        divisors = []

        if last == 0:
            roots.append(0.0)
            current_coefs = current_coefs[:-1]
            continue

        for i in range(1, int(abs(last)) + 1):
            if last % i == 0:
                divisors.append(i)
                divisors.append(-i)
        divisors.append(int(last))
        if last != 0:
            divisors.append(-int(last))

        divisors = sorted(list(set(divisors)))

        root_found = False
        for divisor in divisors:
            power = len(current_coefs) - 1
            total = 0
            for coef in current_coefs:
                total += coef * (divisor ** power)
                power -= 1

            if abs(total) == 0.0:
                roots.append(divisor)
                current_coefs = decomposition(divisor, current_coefs)
                current_coefs = current_coefs[:-1]
                root_found = True
                break

    if len(current_coefs) == 3:
        a, b, c = current_coefs
        roots = get_roots(a, b, c)

    return roots

alphabet = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']

def main():
    coefs = get_coefs()

    str = []
    for i in range(len(coefs) - 1, -1, -1):
        str.append(f'{alphabet[i].upper()}x^{i}')
    print(f"\nУравнение: {' + '.join(str)}")

    roots = get_roots(coefs)

    for i in range(len(roots)):
        print(f'x{i + 1} = {roots[i]}')

if __name__ == "__main__":
    main()

# Пример запуска
# 1 -10 35 -50 24
