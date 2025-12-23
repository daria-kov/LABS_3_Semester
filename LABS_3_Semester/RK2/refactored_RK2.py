class Student:

    def __init__(self, id, fio, grade, class_id):
        self.id = id
        self.fio = fio
        self.grade = grade
        self.class_id = class_id

    def __repr__(self):
        return f"Student(id={self.id}, fio='{self.fio}', grade={self.grade}, class_id={self.class_id})"


class SchoolClass:

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __repr__(self):
        return f"SchoolClass(id={self.id}, name='{self.name}')"


class StudentClass:

    def __init__(self, class_id, student_id):
        self.class_id = class_id
        self.student_id = student_id

    def __repr__(self):
        return f"StudentClass(class_id={self.class_id}, student_id={self.student_id})"


class SchoolDataProcessor:

    def __init__(self, classes, students, students_classes):
        self.classes = classes
        self.students = students
        self.students_classes = students_classes

    def get_one_to_many_data(self):
        return [
            [stud.fio, stud.grade, cl.name]
            for stud in self.students
            for cl in self.classes
            if stud.class_id == cl.id
        ]

    def get_classes_with_student_count(self):
        one_to_many = self.get_one_to_many_data()
        result = []

        for cl in self.classes:
            studs_in_class = list(filter(lambda x: x[2] == cl.name, one_to_many))
            if studs_in_class:
                result.append((cl.name, len(studs_in_class)))

        return sorted(result, key=lambda x: x[1])

    def get_many_to_many_data(self):
        many_to_many_first = [
            [cl.name, sc.class_id, sc.student_id]
            for cl in self.classes
            for sc in self.students_classes
            if cl.id == sc.class_id
        ]

        return [
            [stud.fio, class_name]
            for class_name, class_id, stud_id in many_to_many_first
            for stud in self.students
            if stud.id == stud_id
        ]

    def get_students_with_ov_ending(self):
        many_to_many = self.get_many_to_many_data()
        result = []

        for fio, class_name in many_to_many:
            if fio.endswith("ов"):
                result.append([fio, class_name])

        return sorted(result, key=lambda x: x[0])

    def get_students_sorted_by_name(self):
        one_to_many = self.get_one_to_many_data()
        return sorted(one_to_many, key=lambda x: x[0])


def main():
    classes = [
        SchoolClass(1, "7А"),
        SchoolClass(2, "7Б"),
        SchoolClass(3, "8В"),
        SchoolClass(4, "8Г"),
    ]

    students = [
        Student(1, "Иванов", 4.5, 1),
        Student(2, "Петров", 3.8, 2),
        Student(3, "Сидоров", 4.2, 3),
        Student(4, "Кузнец", 4.8, 3),
        Student(5, "Никитин", 3.9, 3),
        Student(6, "Беляев", 4.1, 4),
    ]

    students_classes = [
        StudentClass(1, 1),
        StudentClass(3, 2),
        StudentClass(3, 3),
        StudentClass(3, 4),
        StudentClass(2, 5),
        StudentClass(4, 6),
        StudentClass(4, 2),
        StudentClass(2, 1),
    ]

    processor = SchoolDataProcessor(classes, students, students_classes)

    print("--- Запрос Б1 ---")
    print("Список всех связанных школьников и классов (1:М), отсортированный по школьникам:")
    arr1 = processor.get_students_sorted_by_name()
    for item in arr1:
        print(f" Школьник: {item[0]}, Оценка: {item[1]}, Класс: {item[2]}")

    print("\n--- Запрос Б2 ---")
    print("Список классов с количеством школьников в каждом (1:М), отсортированный по количеству (по возрастанию):")
    arr2 = processor.get_classes_with_student_count()
    for item in arr2:
        print(f" Класс: {item[0]}, Количество школьников: {item[1]}")

    print("\n--- Запрос Б3 ---")
    print("Список всех школьников, у которых фамилия заканчивается на 'ов', и названия их классов (М:М):")
    arr3 = processor.get_students_with_ov_ending()
    for item in arr3:
        print(f" Школьник: {item[0]}, Класс: {item[1]}")


if __name__ == "__main__":
    main()
