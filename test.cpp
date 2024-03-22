#include<iostream>

int main() {
    int num = 1;
    if(*(char *)&num == 1) {
        std::cout << "Little-Endian";
    } else {
        std::cout << "Big-Endian";
    }
    return 0;
}