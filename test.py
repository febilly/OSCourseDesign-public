from abc import ABC, abstractmethod

class AbstractClassExample(ABC):
    @abstractmethod
    def do_something(self):
        pass

    def another_method(self):
        self.do_something()

class AnotherClass(AbstractClassExample):
    def do_something(self):
        print("The abstract method is being called")

# 创建一个AnotherClass的实例
x = AnotherClass()
x.do_something()
x.another_method()