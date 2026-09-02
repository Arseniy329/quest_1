first_number = int(input("Enter the first number: "))

second_number = int(input("Enter the second number: "))

operation = input("Enter the operation (+, -, *, /): ")
if operation == "+":
    result = first_number + second_number
elif operation == "-":
    result = first_number - second_number
elif operation == "*":
    result = first_number * second_number
elif operation == "/":
    result = first_number / second_number
else:
    result = "Invalid operation"
print("The result is:", result)