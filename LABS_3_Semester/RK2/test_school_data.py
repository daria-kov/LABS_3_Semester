import unittest
from refactored_RK1 import Student, SchoolClass, StudentClass, SchoolDataProcessor


class TestSchoolDataProcessor(unittest.TestCase):

    def setUp(self):
        self.classes = [
            SchoolClass(1, "7А"),
            SchoolClass(2, "7Б"),
            SchoolClass(3, "8В"),
            SchoolClass(4, "8Г"),
        ]

        self.students = [
            Student(1, "Иванов", 4.5, 1),
            Student(2, "Петров", 3.8, 2),
            Student(3, "Сидоров", 4.2, 3),
            Student(4, "Кузнец", 4.8, 3),
            Student(5, "Никитин", 3.9, 3),
            Student(6, "Беляев", 4.1, 4),
        ]

        self.students_classes = [
            StudentClass(1, 1),
            StudentClass(3, 2),
            StudentClass(3, 3),
            StudentClass(3, 4),
            StudentClass(2, 5),
            StudentClass(4, 6),
            StudentClass(4, 2),
            StudentClass(2, 1),
        ]

        self.processor = SchoolDataProcessor(
            self.classes,
            self.students,
            self.students_classes
        )

    def test_get_one_to_many_data(self):
        result = self.processor.get_one_to_many_data()

        self.assertEqual(len(result), 6, "Неверное количество записей 1:М")

        for item in result:
            self.assertEqual(len(item), 3, "Неверная структура записи")
            self.assertIsInstance(item[0], str, "ФИО должно быть строкой")
            self.assertIsInstance(item[1], float, "Оценка должна быть числом")
            self.assertIsInstance(item[2], str, "Название класса должно быть строкой")

        student_names = [item[0] for item in result]
        self.assertIn("Иванов", student_names, "Иванов должен быть в списке")
        self.assertIn("Петров", student_names, "Петров должен быть в списке")

    def test_get_classes_with_student_count(self):
        """Тест 2: Проверка подсчета школьников по классам."""
        result = self.processor.get_classes_with_student_count()

        counts = [count for _, count in result]
        self.assertEqual(counts, sorted(counts), "Список должен быть отсортирован по количеству")

        for class_name, count in result:
            self.assertIsInstance(class_name, str, "Название класса должно быть строкой")
            self.assertIsInstance(count, int, "Количество должно быть целым числом")
            self.assertGreaterEqual(count, 0, "Количество не может быть отрицательным")

        class_dict = dict(result)
        self.assertEqual(class_dict.get("8В"), 3, "В классе 8В должно быть 3 школьника")
        self.assertEqual(class_dict.get("7А"), 1, "В классе 7А должен быть 1 школьник")

    def test_get_students_with_ov_ending(self):
        """Тест 3: Проверка поиска школьников с фамилиями на 'ов'."""
        result = self.processor.get_students_with_ov_ending()

        surnames = [item[0] for item in result]
        self.assertEqual(surnames, sorted(surnames), "Список должен быть отсортирован по фамилии")

        for surname, _ in result:
            self.assertTrue(surname.endswith("ов"), f"Фамилия '{surname}' должна заканчиваться на 'ов'")

        for surname, class_name in result:
            self.assertIsInstance(surname, str, "Фамилия должна быть строкой")
            self.assertIsInstance(class_name, str, "Название класса должно быть строкой")

        found_surnames = [item[0] for item in result]
        self.assertIn("Иванов", found_surnames, "Иванов должен быть найден")
        self.assertIn("Петров", found_surnames, "Петров должен быть найден")
        self.assertIn("Сидоров", found_surnames, "Сидоров должен быть найден")
        self.assertNotIn("Кузнец", found_surnames, "Кузнец не должен быть найден")

    def test_edge_cases(self):
        empty_processor = SchoolDataProcessor([], [], [])
        self.assertEqual(empty_processor.get_one_to_many_data(), [])
        self.assertEqual(empty_processor.get_classes_with_student_count(), [])
        self.assertEqual(empty_processor.get_students_with_ov_ending(), [])

        self.assertEqual(empty_processor.get_students_sorted_by_name(), [])

    def test_data_consistency(self):
        one_to_many = self.processor.get_one_to_many_data()
        class_names = {cl.name for cl in self.classes}

        for _, _, class_name in one_to_many:
            self.assertIn(class_name, class_names, f"Класс '{class_name}' не существует")

        many_to_many = self.processor.get_many_to_many_data()
        student_ids = {stud.id for stud in self.students}

        many_to_many_first = [
            [cl.name, sc.class_id, sc.student_id]
            for cl in self.classes
            for sc in self.students_classes
            if cl.id == sc.class_id
        ]

        for _, class_id, student_id in many_to_many_first:
            self.assertIn(student_id, student_ids, f"Студент с id={student_id} не существует")
            self.assertIn(class_id, [cl.id for cl in self.classes], f"Класс с id={class_id} не существует")


if __name__ == "__main__":
    unittest.main(verbosity=2)
