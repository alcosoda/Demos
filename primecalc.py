def count_primes(n):
    """Возвращает количество простых чисел до n (не включая n)"""
    if n <= 2:
        return 0
    
    # Создаем массив для отслеживания простых чисел (решето Эратосфена)
    is_prime = [True] * n
    is_prime[0] = is_prime[1] = False
    
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            # Отмечаем все кратные i как составные
            for j in range(i*i, n, i):
                is_prime[j] = False
    
    return sum(is_prime)

if __name__ == "__main__":
    try:
        n = int(input("Введите число N: "))
        if n < 0:
            print("Пожалуйста, введите неотрицательное число.")
        else:
            result = count_primes(n)
            print(f"Количество простых чисел до {n}: {result}")
    except ValueError:
        print("Ошибка: пожалуйста, введите целое число.")
