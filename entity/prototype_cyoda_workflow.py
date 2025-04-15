class Application:
    def __init__(self):
        self.data = []
        self.require_additional_questions = False

    def add_data(self, item):
        if item not in self.data:  # Prevent duplicates
            self.data.append(item)
        else:
            print(f"Item '{item}' already exists in the data.")

    def remove_data(self, item):
        try:
            self.data.remove(item)
        except ValueError:
            print(f"Item '{item}' not found in the data.")

    def display_data(self):
        if self.data:
            print("Current Data:")
            for item in self.data:
                print(f"- {item}")
        else:
            print("No data available.")

    def clear_data(self):
        self.data.clear()
        print("All data has been cleared.")

    def set_require_additional_questions(self, value):
        if isinstance(value, bool):
            self.require_additional_questions = value
            print(f"Require additional questions set to {self.require_additional_questions}.")
        else:
            print("Invalid value. Please provide a boolean.")

    def finish_discussion(self):
        print("Discussion finished. Exiting application.")
        self.clear_data()  # Clear data on exit


if __name__ == "__main__":
    app = Application()
    app.set_require_additional_questions(False)  # Set to False as per requirement
    app.add_data("Sample Item 1")
    app.add_data("Sample Item 2")
    app.display_data()
    app.remove_data("Sample Item 1")
    app.display_data()
    app.finish_discussion()
