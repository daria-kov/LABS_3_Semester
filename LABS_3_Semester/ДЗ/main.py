"""Main test file for Deep Research Agent with GigaChat - Interactive Version."""

import asyncio
import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Импортируем локальные модули
try:
    import configuration
    import utils
    import state
    import prompts
    import deep_researcher

    # Получаем graph
    deep_researcher_graph = deep_researcher.deep_researcher_graph

    print("Все модули импортированы успешно")

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("\nФайлы в текущей директории:")
    for f in os.listdir('.'):
        print(f"  - {f}")
    exit(1)

def display_thought_summary():
    """Отображает краткую сводку мыслей агента."""
    from utils import thought_logger
    thoughts = thought_logger.get_all_thoughts()

    if thoughts:
        print("\n" + "="*60)
        print("СВОДКА МЫСЛЕННОГО ПРОЦЕССА АГЕНТА")
        print("="*60)

        agent_types = {}
        for thought in thoughts:
            agent_type = thought["agent_type"]
            agent_types[agent_type] = agent_types.get(agent_type, 0) + 1

        print("Статистика по агентам:")
        for agent, count in agent_types.items():
            print(f"   • {agent}: {count} размышлений")

        print("\nВременная шкала процесса:")
        for i, thought in enumerate(thoughts[:10]):  # Показываем первые 10 мыслей
            print(f"   {i+1:2d}. [{thought['timestamp']}] {thought['agent_type']}: {thought['thought'][:80]}...")

        if len(thoughts) > 10:
            print(f"   ... и еще {len(thoughts) - 10} размышлений")

        print("="*60)

async def interactive_research_session():
    """Интерактивная сессия исследования с обработкой уточнений."""

    print("\n" + "="*60)
    print("ИНТЕРАКТИВНАЯ СЕССИЯ ИССЛЕДОВАНИЯ")
    print("="*60)

    # Очищаем логи мыслей перед новой сессией
    from utils import thought_logger
    thought_logger.clear()

    # Запрашиваем начальный вопрос у пользователя
    initial_query = input("\nВведите ваш исследовательский запрос: ").strip()

    if not initial_query:
        print("Запрос не может быть пустым")
        return

    # Конфигурация
    config = {
        "configurable": {
            "research_model": "gigachat:gigachat-2-max",
            "summarization_model": "gigachat:gigachat-2-max",
            "compression_model": "gigachat:gigachat-2-max",
            "final_report_model": "gigachat:gigachat-2-max",
            "search_api": "tavily",
            "max_concurrent_research_units": 1,
            "max_researcher_iterations": 3,
            "max_react_tool_calls": 3,
            "allow_clarification": True,  # Включаем уточнения
            "apiKeys": {
                "GIGACHAT_API_KEY": os.getenv("GIGACHAT_API_KEY"),
                "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY")
            }
        }
    }

    # Начальное состояние
    state = {
        "messages": [HumanMessage(content=initial_query)]
    }

    print(f"\nАнализирую запрос: '{initial_query}'")

    # Цикл взаимодействия
    iteration = 0
    max_iterations = 5  # Максимум 5 итераций уточнений

    while iteration < max_iterations:
        iteration += 1

        print(f"\nИтерация {iteration}/{max_iterations}...")

        # Выполняем шаг агента
        try:
            result = await deep_researcher_graph.ainvoke(state, config)
        except Exception as e:
            print(f"Ошибка при выполнении агента: {e}")
            break

        # Обновляем состояние
        state = result

        # Проверяем, есть ли последнее сообщение
        if not result.get("messages"):
            print("Нет сообщений в результате")
            break

        last_message = result["messages"][-1]

        # Если агент запрашивает уточнение
        if isinstance(last_message, AIMessage) and last_message.content:
            print(f"\nАгент: {last_message.content}")

            # Проверяем, завершился ли процесс
            if result.get("final_report"):
                print("\nИсследование завершено!")
                display_thought_summary()
                print("\n" + "="*80)
                print("ФИНАЛЬНЫЙ ОТЧЕТ:")
                print("="*80)
                print(result["final_report"])
                print("="*80)
                break

            # Запрашиваем ответ пользователя
            user_response = input("\nВаш ответ (или 'стоп' для завершения): ").strip()

            if user_response.lower() in ['стоп', 'stop', 'выход', 'exit', 'quit']:
                print("Завершение сессии")
                display_thought_summary()
                break

            if not user_response:
                print("Ответ не может быть пустым, попробуйте снова")
                iteration -= 1
                continue

            # Добавляем ответ пользователя в историю сообщений
            state["messages"].append(HumanMessage(content=user_response))

        elif result.get("final_report"):
            # Если есть финальный отчет, показываем его
            print("\nИсследование завершено!")
            display_thought_summary()
            print("\n" + "="*80)
            print("ФИНАЛЬНЫЙ ОТЧЕТ:")
            print("="*80)
            print(result["final_report"])
            print("="*80)
            break

        else:
            # Если что-то пошло не так
            print("\nНеожиданное состояние агента")
            if result.get("notes"):
                print(f"Заметки: {len(result['notes'])} шт.")
            break

    if iteration >= max_iterations:
        print("\nДостигнуто максимальное количество итераций")
        display_thought_summary()
        if result.get("final_report"):
            print("\nПоследний отчет:")
            print(result["final_report"][:500] + "...")

async def quick_test_no_clarification():
    """Быстрый тест без уточнений."""

    print("\n" + "="*60)
    print("БЫСТРЫЙ ТЕСТ БЕЗ УТОЧНЕНИЙ")
    print("="*60)

    # Очищаем логи мыслей перед новой сессией
    from utils import thought_logger
    thought_logger.clear()

    config = {
        "configurable": {
            "research_model": "gigachat:gigachat-2-max",
            "summarization_model": "gigachat:gigachat-2-max",
            "compression_model": "gigachat:gigachat-2-max",
            "final_report_model": "gigachat:gigachat-2-max",
            "search_api": "tavily",
            "max_concurrent_research_units": 1,
            "max_researcher_iterations": 2,
            "max_react_tool_calls": 2,
            "allow_clarification": False,  # Отключаем уточнения
            "apiKeys": {
                "GIGACHAT_API_KEY": os.getenv("GIGACHAT_API_KEY"),
                "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY")
            }
        }
    }

    test_query = "Какие достопримечательности посмотреть в Москве за один день?"

    print(f"\nЗапрос: {test_query}")
    print("Выполнение исследования...")

    state = {
        "messages": [HumanMessage(content=test_query)]
    }

    try:
        result = await deep_researcher_graph.ainvoke(state, config)

        if result.get("final_report"):
            print("\nИсследование завершено!")
            display_thought_summary()
            print(f"\nДлина отчета: {len(result['final_report'])} символов")
            print("\nПервые 800 символов отчета:")
            print("="*60)
            print(result["final_report"][:800] + "...")
            print("="*60)
        else:
            print("\n Финальный отчет не сгенерирован")
            display_thought_summary()
            if result.get("messages"):
                print(f"\nПоследнее сообщение: {result['messages'][-1].content[:200]}...")

    except Exception as e:
        print(f"Ошибка: {e}")

async def check_connections():
    """Проверка подключений к API."""

    print("Проверка подключений...")

    # Проверка GigaChat
    api_key = os.getenv("GIGACHAT_API_KEY")
    if not api_key:
        print("GIGACHAT_API_KEY не найден")
        return False

    print(f"GigaChat API ключ: {'*' * min(20, len(api_key))}...")

    # Проверка Tavily
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        print("TAVILY_API_KEY не найден - поиск отключен")
        return False

    print(f"Tavily API ключ: {'*' * min(10, len(tavily_key))}...")

    return True

def print_menu():
    """Печать меню выбора."""

    print("\n" + "="*60)
    print("DEEP RESEARCH AGENT - МЕНЮ")
    print("="*60)
    print("1. Интерактивная сессия (вопрос-ответ с агентом)")
    print("2. Быстрый тест без уточнений")
    print("3. Информация о системе")
    print("4. Выход")
    print("="*60)

def print_system_info():
    """Вывод информации о системе."""

    print("\n" + "="*60)
    print("ИНФОРМАЦИЯ О СИСТЕМЕ")
    print("="*60)

    print(f" Модель: GigaChat-2-Max")
    print(f" Поиск: {'Tavily' if os.getenv('TAVILY_API_KEY') else ' Отключен'}")
    print(f" Уточнения: Включены в интерактивном режиме")
    print(f" Логирование мыслей: Включено")
    print(f" Файлы проекта:")

    files = [f for f in os.listdir('.') if f.endswith('.py')]
    for file in sorted(files):
        print(f"  • {file}")

    print("\n Примеры запросов для тестирования:")
    print("  • 'Лучшие кофейни в Москве с Wi-Fi'")
    print("  • 'Сравнение iPhone 15 и Samsung Galaxy S24'")
    print("  • 'Как начать изучать программирование с нуля?'")
    print("  • 'Новейшие разработки в области искусственного интеллекта'")

async def main():
    """Основная функция."""

    print("Deep Research Agent - Interactive GigaChat Edition")
    print(" Версия с выводом мыслей агента")

    # Проверяем подключения
    if not await check_connections():
        print("\nПроверьте настройки API ключей в файле .env")
        return

    # Основной цикл меню
    while True:
        print_menu()

        try:
            choice = input("\nВыберите вариант (1-5): ").strip()

            if choice == "1":
                await interactive_research_session()
            elif choice == "2":
                await quick_test_no_clarification()
            elif choice == "3":
                await test_with_thoughts_demo()
            elif choice == "4":
                print_system_info()
            elif choice == "5":
                print("\nДо свидания!")
                break
            else:
                print("Неверный выбор. Попробуйте снова.")

            input("\n↵ Нажмите Enter для продолжения...")

        except KeyboardInterrupt:
            print("\n\nЗавершение программы...")
            break
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    # Устанавливаем политику событий для Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма завершена пользователем")
