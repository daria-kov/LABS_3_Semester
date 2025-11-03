import sys
import math

def get_coef(index, prompt):
    while True:
        try:
            if len(sys.argv) > index:
                coef_str = sys.argv[index]
                print(f"{prompt} {coef_str}")
            else:
                print(prompt)
                coef_str = input()

            coef = float(coef_str)
            return coef
        except (ValueError, IndexError):
            if len(sys.argv) > index:
                print(f"Некорректное значение коэффициента. {prompt}")
                sys.argv = sys.argv[:index]

def solve_biquadratic(a, b, c):
    result = []

    if a == 0:
        if b == 0:
            if c == 0:
                print("Уравнение имеет бесконечное количество решений")
            return result
        else:
            x_squared = -c / b
            if x_squared > 0:
                root = math.sqrt(x_squared)
                result.append(root)
                result.append(-root)
            elif x_squared == 0:
                result.append(0.0)
            return result

    D = b*b - 4*a*c

    if D < 0:
        return result
    elif D == 0:
        y = -b / (2*a)
        if y > 0:
            root1 = math.sqrt(y)
            root2 = -math.sqrt(y)
            result.append(root1)
            result.append(root2)
        elif y == 0:
            result.append(0.0)
    else:
        sqrt_D = math.sqrt(D)
        y1 = (-b + sqrt_D) / (2*a)
        y2 = (-b - sqrt_D) / (2*a)

        if y1 > 0:
            root1 = math.sqrt(y1)
            root2 = -math.sqrt(y1)
            result.append(root1)
            result.append(root2)
        elif y1 == 0:
            result.append(0.0)

        if y2 > 0:
            root3 = math.sqrt(y2)
            root4 = -math.sqrt(y2)
            if root3 not in result:
                result.append(root3)
            if root4 not in result:
                result.append(root4)
        elif y2 == 0 and 0.0 not in result:
            result.append(0.0)

    result.sort()
    return result


def main():
    print("Решение биквадратного уравнения Ax⁴ + Bx² + C = 0")

    a = get_coef(1, 'Введите коэффициент A:')
    b = get_coef(2, 'Введите коэффициент B:')
    c = get_coef(3, 'Введите коэффициент C:')

    print(f"\nУравнение: {a}x⁴ + {b}x² + {c} = 0")

    roots = solve_biquadratic(a, b, c)

    len_roots = len(roots)
    if len_roots == 0:
        print('Действительных корней нет')
    elif len_roots == 1:
        print('Один корень: x = {}'.format(roots[0]))
    elif len_roots == 2:
        print('Два корня: x₁ = {}, x₂ = {}'.format(roots[0], roots[1]))
    elif len_roots == 3:
        print('Три корня: x₁ = {}, x₂ = {}, x₃ = {}'.format(roots[0], roots[1], roots[2]))
    elif len_roots == 4:
        print('Четыре корня: x₁ = {}, x₂ = {}, x₃ = {}, x₄ = {}'.format(
            roots[0], roots[1], roots[2], roots[3]))

if __name__ == "__main__":
    main()


# Примеры запуска:
# python biquadratic.py 1 0 -4    (уравнение x⁴ - 4 = 0, корни ±√2)
# python biquadratic.py 1 -5 4     (уравнение x⁴ - 5x² + 4 = 0, корни ±1, ±2)
# python biquadratic.py 1 0 0      (уравнение x⁴ = 0, корень 0)
