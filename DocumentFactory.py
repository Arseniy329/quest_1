from abc import ABC, abstractmethod

class Document(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

class Report(Document):
    def render(self) -> str:
        return "Звіт по документу"

class Invoice(Document):
    def render(self) -> str:
        return "Запит на оплату"

class Contract(Document):
    def render(self) -> str:
        return "Договір"

class DocumentFactory:
    register: dict[str, type[Document]] = {
        "report": Report,
        "invoice": Invoice,
        "contract": Contract,
    }

    @staticmethod
    def create(doc_type: str) -> Document:
        doc_class = DocumentFactory.register.get(doc_type.lower().strip() if isinstance(doc_type, str) else "")
        if not doc_class:
            raise ValueError(f"Ви ввели неправильний формат даних для документа: {doc_type}")
        return doc_class()

if __name__ == "__main__":
    input_types = ["report", "invoice", "contract"]

    for doc_type in input_types:
        document = DocumentFactory.create(doc_type)
        print(document.render())