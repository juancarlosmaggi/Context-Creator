import timeit
import random

# Generate a large set of strings
num_elements = 100000
elements_set = {f"/path/to/some/file_{i}.txt" for i in range(num_elements)}

def sort_with_list():
    return sorted(list(elements_set), key=str)

def sort_without_list():
    return sorted(elements_set, key=str)

if __name__ == "__main__":
    time_with_list = timeit.timeit(sort_with_list, number=100)
    time_without_list = timeit.timeit(sort_without_list, number=100)

    print(f"Time with list(): {time_with_list:.4f} seconds")
    print(f"Time without list(): {time_without_list:.4f} seconds")
    print(f"Improvement: {(time_with_list - time_without_list) / time_with_list * 100:.2f}%")
