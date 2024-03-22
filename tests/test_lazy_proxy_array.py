import unittest
from lazy_proxy_array import ObjectProxy, LazyProxyArray

writebacks = []

class TestObjectProxy(unittest.TestCase):
    def setUp(self):
        writebacks.clear()

        class TestObject:
            def __init__(self):
                self.value = 0
                self.nested = {'a': 10}

            def writeback_method(self):
                writebacks.append(True)

        self.test_obj = TestObject()
        self.proxy = ObjectProxy(self.test_obj, self.test_obj.writeback_method)

    def test_attribute_access_and_modification(self):
        # 测试属性访问
        self.assertEqual(self.proxy.value, 0)
        # 测试属性修改
        self.proxy.value = 100
        self.assertEqual(self.test_obj.value, 100)
        self.assertEqual(len(writebacks), 1)

    def test_nested_object_proxy(self):
        # 测试嵌套对象代理
        self.assertEqual(self.proxy.nested['a'], 10)
        self.proxy.nested['a'] = 20
        self.assertEqual(self.test_obj.nested['a'], 20)
        self.assertEqual(len(writebacks), 1)

class TestLazyProxyArray(unittest.TestCase):
    def setUp(self):
        self.array = [10, 20, 30, 40, 50]
        writebacks.clear()

        def getter(index):
            return self.array[index]

        def setter(index, value):
            self.array[index] = value
            writebacks.append(index)

        self.lazy_array = LazyProxyArray(len(self.array), getter, setter)

    def test_item_access_and_modification(self):
        # 测试项访问
        self.assertEqual(self.lazy_array[1], 20)
        # 测试项修改
        self.lazy_array[1] = 200
        self.assertEqual(self.array[1], 200)
        self.assertIn(1, writebacks)

    def test_iteration(self):
        # 测试迭代
        for i, item in enumerate(self.lazy_array):
            self.assertEqual(item, self.array[i])

if __name__ == "__main__":
    unittest.main()