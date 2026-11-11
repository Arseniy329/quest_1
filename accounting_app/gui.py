"""
Графічний інтерфейс користувача (GUI) на Tkinter / ttk.
Відповідає всім вимогам щодо оптимізації для застарілого обладнання,
інтерфейсу українською мовою та суворого відокремлення сховища (Repository Pattern).
"""

from datetime import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

from .models import Product
from .repository import ProductRepository, StorageError, StorageFormatError
from .validator import ProductValidator


class AccountingApp(tk.Tk):
    """
    Головне вікно програми складського обліку товарів.

    Клас вікна НЕ знає про внутрішній формат збереження даних (CSV).
    Вся робота з даними відбувається виключно через інтерфейс ProductRepository.
    """

    COLOR_BG = "#F4F6F9"
    COLOR_CARD = "#FFFFFF"
    COLOR_BORDER = "#D0D7DE"
    COLOR_ERROR_BG = "#FFEAEB"
    COLOR_ERROR_BORDER = "#CF222E"
    COLOR_PRIMARY = "#0969DA"
    COLOR_TEXT = "#1F2328"

    def __init__(self, repository: ProductRepository):
        super().__init__()
        self.repository = repository

        # Стан інтерфейсу
        self.selected_product_id: Optional[str] = None
        self.sort_column: str = "id"
        self.sort_descending: bool = False
        self.field_entries: Dict[str, tk.Widget] = {}
        self.field_wrappers: Dict[str, tk.Frame] = {}

        # Базові налаштування вікна
        self.title("Складський облік товарів — [Новий список]")
        self.geometry("1100x680")
        self.minsize(880, 560)
        self.configure(bg=self.COLOR_BG)

        # Центрування вікна на екрані
        self._center_window()

        # Налаштування стилів ttk
        self._configure_styles()

        # Побудова компонентів
        self._create_menu()
        self._create_search_bar()
        self._create_main_content()
        self._create_status_bar()

        # Гарячі клавіші та події закриття
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Початкове завантаження таблиці
        self.refresh_table()
        self.set_status("Програма готова до роботи. Створіть або відкрийте файл для обліку.")

    # -------------------------------------------------------------------------
    # Ініціалізація стилів та геометрії
    # -------------------------------------------------------------------------

    def _center_window(self) -> None:
        """Центрує головне вікно на екрані користувача."""
        self.update_idletasks()
        width = 1100
        height = 680
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = max(0, (screen_w - width) // 2)
        pos_y = max(0, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    def _configure_styles(self) -> None:
        """Налаштовує стиль елементів ttk для чистого, сучасного вигляду."""
        self.style = ttk.Style(self)
        # Використовуємо універсальну тему для максимальної сумісності
        available_themes = self.style.theme_names()
        for preferred in ("clam", "alt", "default"):
            if preferred in available_themes:
                self.style.theme_use(preferred)
                break

        # Таблиця
        self.style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground="#1F2328",
            fieldbackground="#FFFFFF",
            rowheight=26,
            font=("Segoe UI", 9) if os.name == "nt" else ("Helvetica", 10),
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold") if os.name == "nt" else ("Helvetica", 10, "bold"),
            foreground="#24292F",
            padding=5,
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#0969DA")],
            foreground=[("selected", "#FFFFFF")],
        )

        # Фіксація темної теми macOS для випадаючих списків (Combobox)
        self.option_add("*TCombobox*Listbox.background", "#FFFFFF")
        self.option_add("*TCombobox*Listbox.foreground", "#1F2328")
        self.option_add("*TCombobox*Listbox.selectBackground", "#0969DA")
        self.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")

        # Кнопки
        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 9, "bold") if os.name == "nt" else ("Helvetica", 10, "bold"),
            padding=6,
        )
        self.style.configure(
            "Action.TButton",
            font=("Segoe UI", 9) if os.name == "nt" else ("Helvetica", 10),
            padding=5,
        )

    # -------------------------------------------------------------------------
    # Меню програми
    # -------------------------------------------------------------------------

    def _create_menu(self) -> None:
        """Створює головне меню програми."""
        menubar = tk.Menu(self)

        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новий список", accelerator="Ctrl+N", command=self.on_file_new)
        file_menu.add_command(label="Відкрити...", accelerator="Ctrl+O", command=self.on_file_open)
        file_menu.add_separator()
        file_menu.add_command(label="Зберегти", accelerator="Ctrl+S", command=self.on_file_save)
        file_menu.add_command(label="Зберегти як...", accelerator="Ctrl+Shift+S", command=self.on_file_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Вихід", accelerator="Alt+F4", command=self.on_close)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню "Довідка"
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Про програму", command=self._show_about)
        menubar.add_cascade(label="Довідка", menu=help_menu)

        self.config(menu=menubar)

    # -------------------------------------------------------------------------
    # Верхня панель пошуку
    # -------------------------------------------------------------------------

    def _create_search_bar(self) -> None:
        """Створює верхню панель швидкого пошуку та фільтрації товарів."""
        search_frame = tk.Frame(self, bg=self.COLOR_BG, padx=14, pady=8)
        search_frame.pack(side=tk.TOP, fill=tk.X)

        lbl = tk.Label(
            search_frame,
            text="Пошук товару:",
            bg=self.COLOR_BG,
            font=("Segoe UI", 10, "bold") if os.name == "nt" else ("Helvetica", 10, "bold"),
            fg=self.COLOR_TEXT,
        )
        lbl.pack(side=tk.LEFT, padx=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.on_search_changed())

        search_wrap = tk.Frame(
            search_frame,
            bg=self.COLOR_BORDER,
            padx=1,
            pady=1,
        )
        search_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.search_entry = tk.Entry(
            search_wrap,
            textvariable=self.search_var,
            font=("Segoe UI", 10) if os.name == "nt" else ("Helvetica", 10),
            bg="#FFFFFF",
            fg=self.COLOR_TEXT,
            insertbackground=self.COLOR_TEXT,
            selectbackground=self.COLOR_PRIMARY,
            selectforeground="#FFFFFF",
            relief="flat",
        )
        self.search_entry.pack(fill=tk.BOTH, ipady=4, ipadx=4)

        btn_clear = ttk.Button(
            search_frame,
            text="Очистити",
            command=self._clear_search,
            style="Action.TButton",
        )
        btn_clear.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_search_count = tk.Label(
            search_frame,
            text="0 товарів",
            bg=self.COLOR_BG,
            fg="#57606A",
            font=("Segoe UI", 9) if os.name == "nt" else ("Helvetica", 9),
        )
        self.lbl_search_count.pack(side=tk.RIGHT)

    def _clear_search(self) -> None:
        """Скидає рядок пошуку."""
        self.search_var.set("")
        self.search_entry.focus_set()

    # -------------------------------------------------------------------------
    # Основний контент (Таблиця зліва, форма справа)
    # -------------------------------------------------------------------------

    def _create_main_content(self) -> None:
        """Створює головну робочу зону: таблицю товарів та картку редагування."""
        container = tk.Frame(self, bg=self.COLOR_BG, padx=14, pady=4)
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Ліва частина — Таблиця товарів
        table_frame = tk.Frame(container, bg=self.COLOR_CARD, relief="solid", bd=1)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self._create_treeview(table_frame)

        # Права частина — Форма введення / редагування
        form_frame = tk.LabelFrame(
            container,
            text="  Картка товару  ",
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT,
            font=("Segoe UI", 10, "bold") if os.name == "nt" else ("Helvetica", 10, "bold"),
            relief="solid",
            bd=1,
            padx=14,
            pady=12,
        )
        form_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 0))
        form_frame.config(width=340)
        form_frame.pack_propagate(False)

        self._create_edit_form(form_frame)

    def _create_treeview(self, parent: tk.Widget) -> None:
        """Ініціалізує та налаштовує віджет Treeview з подвійним скролбаром."""
        columns = ("id", "name", "category", "quantity", "price", "location")

        self.tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        # Заголовки стовпців
        self.column_headers = {
            "id": "ID",
            "name": "Назва товару",
            "category": "Категорія",
            "quantity": "Кількість, шт.",
            "price": "Ціна, грн.",
            "location": "Розташування",
        }

        col_widths = {
            "id": 90,
            "name": 220,
            "category": 120,
            "quantity": 100,
            "price": 100,
            "location": 120,
        }

        col_align = {
            "id": "center",
            "name": "w",
            "category": "w",
            "quantity": "e",
            "price": "e",
            "location": "w",
        }

        for col in columns:
            self.tree.heading(
                col,
                text=self.column_headers[col],
                command=lambda c=col: self.on_sort_column(c),
            )
            self.tree.column(
                col,
                width=col_widths[col],
                minwidth=60,
                anchor=col_align[col],
            )

        # Смуги прокручування
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Смугасте забарвлення рядків із явним шрифтом кольору для Dark Mode
        self.tree.tag_configure("oddrow", background="#FFFFFF", foreground=self.COLOR_TEXT)
        self.tree.tag_configure("evenrow", background="#F8FAFC", foreground=self.COLOR_TEXT)

        # Подія вибору рядка
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def _create_edit_form(self, parent: tk.Widget) -> None:
        """Створює поля форми редагування та кнопки управління."""
        fields_config = [
            ("id", "ID товару:", "Залиште порожнім для автогенерації"),
            ("name", "Назва товару:*", "Наприклад, Папір А4 Maestro"),
            ("category", "Категорія:*", "Наприклад, Канцтовари"),
            ("quantity", "Кількість, шт.:*", "Ціле невід'ємне число (напр., 50)"),
            ("price", "Ціна за од., грн.:*", "Число (напр., 185.50)"),
            ("location", "Розташування:", "Склад, стелаж, полиця"),
        ]

        row_idx = 0
        for field_id, label_text, tooltip in fields_config:
            lbl = tk.Label(
                parent,
                text=label_text,
                bg=self.COLOR_CARD,
                fg=self.COLOR_TEXT,
                font=("Segoe UI", 9, "bold") if os.name == "nt" else ("Helvetica", 9, "bold"),
                anchor="w",
            )
            lbl.pack(fill=tk.X, pady=(6 if row_idx > 0 else 0, 2))

            # Рамка для підсвічування помилок валідації
            wrapper = tk.Frame(parent, bg=self.COLOR_BORDER, padx=1, pady=1)
            wrapper.pack(fill=tk.X, pady=(0, 2))
            self.field_wrappers[field_id] = wrapper

            if field_id == "category":
                # Використовуємо Combobox для зручного вибору існуючої або введення нової категорії
                entry = ttk.Combobox(wrapper, font=("Segoe UI", 9) if os.name == "nt" else ("Helvetica", 9))
                entry.pack(fill=tk.X)
            else:
                entry = tk.Entry(
                    wrapper,
                    font=("Segoe UI", 9) if os.name == "nt" else ("Helvetica", 9),
                    bg="#FFFFFF",
                    fg=self.COLOR_TEXT,
                    insertbackground=self.COLOR_TEXT,
                    selectbackground=self.COLOR_PRIMARY,
                    selectforeground="#FFFFFF",
                    relief="flat",
                )
                entry.pack(fill=tk.X, ipady=3, ipadx=4)

            # Очищення підсвічування помилки при початку вводу
            entry.bind("<Key>", lambda e, fid=field_id: self._clear_field_error(fid))
            self.field_entries[field_id] = entry
            row_idx += 1

        # Поле інформації про дату створення
        self.lbl_created_at = tk.Label(
            parent,
            text="Створено: —",
            bg=self.COLOR_CARD,
            fg="#6E7781",
            font=("Segoe UI", 8) if os.name == "nt" else ("Helvetica", 8),
            anchor="w",
        )
        self.lbl_created_at.pack(fill=tk.X, pady=(4, 12))

        # Панель кнопок дій
        btn_box = tk.Frame(parent, bg=self.COLOR_CARD)
        btn_box.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))

        # Верхній ряд кнопок: Додати / Оновити
        row1 = tk.Frame(btn_box, bg=self.COLOR_CARD)
        row1.pack(fill=tk.X, pady=(0, 6))

        self.btn_add = ttk.Button(
            row1,
            text="Додати",
            command=self.on_add_product,
            style="Primary.TButton",
        )
        self.btn_add.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_update = ttk.Button(
            row1,
            text="Оновити",
            command=self.on_update_product,
            style="Action.TButton",
        )
        self.btn_update.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        # Нижній ряд кнопок: Видалити / Очистити форму
        row2 = tk.Frame(btn_box, bg=self.COLOR_CARD)
        row2.pack(fill=tk.X)

        self.btn_delete = ttk.Button(
            row2,
            text="Видалити",
            command=self.on_delete_product,
            style="Action.TButton",
        )
        self.btn_delete.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_clear = ttk.Button(
            row2,
            text="Очистити форму",
            command=self.on_clear_form,
            style="Action.TButton",
        )
        self.btn_clear.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

    # -------------------------------------------------------------------------
    # Рядок стану (Status Bar)
    # -------------------------------------------------------------------------

    def _create_status_bar(self) -> None:
        """Створює нижній рядок стану зі статистикою та підказками."""
        self.status_frame = tk.Frame(self, bg="#EAECEF", relief="groove", bd=1, padx=8, pady=3)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.lbl_status = tk.Label(
            self.status_frame,
            text="Готово",
            bg="#EAECEF",
            fg=self.COLOR_TEXT,
            font=("Segoe UI", 9) if os.name == "nt" else ("Helvetica", 9),
            anchor="w",
        )
        self.lbl_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.lbl_stats = tk.Label(
            self.status_frame,
            text="",
            bg="#EAECEF",
            fg="#24292F",
            font=("Segoe UI", 9, "bold") if os.name == "nt" else ("Helvetica", 9, "bold"),
            anchor="e",
        )
        self.lbl_stats.pack(side=tk.RIGHT)

    def set_status(self, message: str, is_error: bool = False) -> None:
        """Виводить повідомлення у status bar."""
        color = self.COLOR_ERROR_BORDER if is_error else self.COLOR_TEXT
        prefix = "⚠️ " if is_error else ""
        self.lbl_status.config(text=f"{prefix}{message}", fg=color)

    def _update_stats(self) -> None:
        """Оновлює агреговані підсумки складу (кількість, загальна сума)."""
        all_items = self.repository.get_all()
        total_items = len(all_items)
        total_qty = sum(p.quantity for p in all_items)
        total_sum = sum(p.total_value() for p in all_items)

        self.lbl_stats.config(
            text=f"Всього: {total_items} тов. | К-сть: {total_qty:,} шт. | Сума: {total_sum:,.2f} грн"
        )

        search_query = self.search_var.get().strip().lower()
        if search_query:
            visible_count = len(self.tree.get_children())
            self.lbl_search_count.config(text=f"Знайдено: {visible_count} з {total_items}")
        else:
            self.lbl_search_count.config(text=f"Всього: {total_items} товарів")

        # Оновлення списку категорій у випадаючому списку
        if isinstance(self.repository, ProductRepository):
            try:
                if hasattr(self.repository, "get_categories"):
                    self.field_entries["category"]["values"] = self.repository.get_categories()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Гарячі клавіші
    # -------------------------------------------------------------------------

    def _bind_shortcuts(self) -> None:
        """Прив'язує гарячі клавіші для швидкої роботи без миші."""
        self.bind("<Control-n>", lambda _: self.on_file_new())
        self.bind("<Control-N>", lambda _: self.on_file_new())
        self.bind("<Control-o>", lambda _: self.on_file_open())
        self.bind("<Control-O>", lambda _: self.on_file_open())
        self.bind("<Control-s>", lambda _: self.on_file_save())
        self.bind("<Control-S>", lambda _: self.on_file_save())
        self.bind("<Control-Shift-s>", lambda _: self.on_file_save_as())
        self.bind("<Control-Shift-S>", lambda _: self.on_file_save_as())
        self.bind("<Control-f>", lambda _: self.search_entry.focus_set())
        self.bind("<Control-F>", lambda _: self.search_entry.focus_set())
        self.bind("<Escape>", lambda _: self._on_escape())
        self.tree.bind("<Delete>", lambda _: self.on_delete_product())

    def _on_escape(self) -> None:
        """Обробка клавіші Escape: скидання пошуку або форми."""
        if self.search_var.get():
            self._clear_search()
        else:
            self.on_clear_form()

    # -------------------------------------------------------------------------
    # Візуальний фідбек валідації
    # -------------------------------------------------------------------------

    def _highlight_field_error(self, field_id: str) -> None:
        """Візуально підсвічує поле з помилкою (червона рамка та світло-червоний фон)."""
        wrapper = self.field_wrappers.get(field_id)
        if wrapper:
            wrapper.config(bg=self.COLOR_ERROR_BORDER)

        entry = self.field_entries.get(field_id)
        if entry:
            if isinstance(entry, tk.Entry) and not isinstance(entry, (ttk.Widget, ttk.Combobox)):
                entry.config(bg=self.COLOR_ERROR_BG, fg=self.COLOR_ERROR_BORDER)

    def _clear_field_error(self, field_id: str) -> None:
        """Знімає підсвічування помилки для конкретного поля."""
        wrapper = self.field_wrappers.get(field_id)
        if wrapper:
            wrapper.config(bg=self.COLOR_BORDER)

        entry = self.field_entries.get(field_id)
        if entry:
            if isinstance(entry, tk.Entry) and not isinstance(entry, (ttk.Widget, ttk.Combobox)):
                entry.config(bg="#FFFFFF", fg=self.COLOR_TEXT)

    def _clear_all_errors(self) -> None:
        """Скидає підсвічування всіх помилок форми."""
        for field_id in self.field_wrappers:
            self._clear_field_error(field_id)

    # -------------------------------------------------------------------------
    # Операції з таблицею Treeview
    # -------------------------------------------------------------------------

    def refresh_table(self, keep_selection: bool = True) -> None:
        """Перезавантажує дані в таблицю з урахуванням пошуку та поточного сортування."""
        selected_id = self.selected_product_id if keep_selection else None

        # Очищення існуючих рядків
        for item in self.tree.get_children():
            self.tree.delete(item)

        items = self.repository.get_all()

        # Фільтрація за пошуковим запитом
        query = self.search_var.get().strip().lower()
        if query:
            items = [
                p
                for p in items
                if query in p.name.lower()
                or query in p.category.lower()
                or query in p.location.lower()
                or query in p.id.lower()
            ]

        # Сортування
        def sort_key(prod: Product):
            val = getattr(prod, self.sort_column)
            if self.sort_column in ("quantity", "price"):
                return val
            return str(val).lower()

        items.sort(key=sort_key, reverse=self.sort_descending)

        # Оновлення заголовків із індикатором сортування
        for col_name, base_text in self.column_headers.items():
            if col_name == self.sort_column:
                arrow = " ▼" if self.sort_descending else " ▲"
                self.tree.heading(col_name, text=f"{base_text}{arrow}")
            else:
                self.tree.heading(col_name, text=base_text)

        # Вставка рядків
        target_iid = None
        for idx, prod in enumerate(items):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            iid = prod.id
            self.tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    prod.id,
                    prod.name,
                    prod.category,
                    f"{prod.quantity:,}",
                    f"{prod.price:,.2f}",
                    prod.location,
                ),
                tags=(tag,),
            )
            if iid == selected_id:
                target_iid = iid

        if target_iid and self.tree.exists(target_iid):
            self.tree.selection_set(target_iid)
            self.tree.see(target_iid)

        self._update_stats()
        self._update_window_title()

    def on_sort_column(self, col: str) -> None:
        """Сортує таблицю за обраним стовпцем або змінює порядок сортування."""
        if self.sort_column == col:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = col
            self.sort_descending = False

        self.refresh_table()

    def on_search_changed(self) -> None:
        """Миттєве фільтрування таблиці під час набору тексту в пошуку."""
        self.refresh_table(keep_selection=True)

    def on_tree_select(self, _event: Optional[tk.Event] = None) -> None:
        """Обробник вибору рядка в таблиці: переносить дані у форму редагування."""
        selected = self.tree.selection()
        if not selected:
            return

        product_id = selected[0]
        product = self.repository.get_by_id(product_id)
        if not product:
            return

        self.selected_product_id = product.id
        self._clear_all_errors()

        # Заповнення полів форми
        self._set_field_value("id", product.id)
        self._set_field_value("name", product.name)
        self._set_field_value("category", product.category)
        self._set_field_value("quantity", str(product.quantity))
        self._set_field_value("price", f"{product.price:.2f}")
        self._set_field_value("location", product.location)
        self.lbl_created_at.config(text=f"Створено: {product.created_at}")

        self.set_status(f"Обрано товар: {product.name} (ID: {product.id})")

    # -------------------------------------------------------------------------
    # Робота з формою (Додати / Оновити / Видалити / Очистити)
    # -------------------------------------------------------------------------

    def _get_form_data(self) -> Dict[str, str]:
        """Отримує словник значень із полів форми."""
        return {
            "id": self._get_field_value("id"),
            "name": self._get_field_value("name"),
            "category": self._get_field_value("category"),
            "quantity": self._get_field_value("quantity"),
            "price": self._get_field_value("price"),
            "location": self._get_field_value("location"),
        }

    def _get_field_value(self, field_id: str) -> str:
        widget = self.field_entries[field_id]
        if isinstance(widget, ttk.Combobox):
            return widget.get().strip()
        return widget.get().strip()

    def _set_field_value(self, field_id: str, value: str) -> None:
        widget = self.field_entries[field_id]
        if isinstance(widget, ttk.Combobox):
            widget.set(value)
        else:
            widget.delete(0, tk.END)
            widget.insert(0, value)

    def on_add_product(self) -> None:
        """Додає новий товар після валідації."""
        self._clear_all_errors()
        data = self._get_form_data()

        result = ProductValidator.validate(
            raw_id=data["id"],
            name=data["name"],
            category=data["category"],
            quantity_str=data["quantity"],
            price_str=data["price"],
            location=data["location"],
            repository=self.repository,
            is_new=True,
        )

        if not result.is_valid:
            for field_id in result.errors:
                self._highlight_field_error(field_id)
            self.set_status(result.first_error_message, is_error=True)
            # Фокус на перше поле з помилкою
            first_err_field = next(iter(result.errors))
            self.field_entries[first_err_field].focus_set()

            error_details = "\n• " + "\n• ".join(result.errors.values())
            messagebox.showwarning(
                "Помилка заповнення форми",
                f"Не вдалося додати товар. Перевірте поля форми:\n{error_details}",
                parent=self,
            )
            return

        product = result.product
        assert product is not None

        try:
            self.repository.add(product)
            self.selected_product_id = product.id
            self.refresh_table()
            self.on_clear_form()
            self._auto_save_if_possible()
            self.set_status(f"Товар '{product.name}' (ID: {product.id}) успішно додано та збережено.")
        except Exception as err:
            messagebox.showerror("Помилка додавання", str(err), parent=self)
            self.set_status(str(err), is_error=True)

    def on_update_product(self) -> None:
        """Оновлює обраний товар після валідації."""
        if not self.selected_product_id:
            messagebox.showinfo(
                "Увага",
                "Будь ласка, оберіть товар у таблиці для оновлення.",
                parent=self,
            )
            self.set_status("Оберіть товар у таблиці для оновлення.", is_error=True)
            return

        current_prod = self.repository.get_by_id(self.selected_product_id)
        if not current_prod:
            messagebox.showerror("Помилка", "Обраний товар не знайдено у сховищі.", parent=self)
            return

        self._clear_all_errors()
        data = self._get_form_data()

        result = ProductValidator.validate(
            raw_id=data["id"],
            name=data["name"],
            category=data["category"],
            quantity_str=data["quantity"],
            price_str=data["price"],
            location=data["location"],
            repository=self.repository,
            is_new=False,
            original_id=self.selected_product_id,
            created_at=current_prod.created_at,
        )

        if not result.is_valid:
            for field_id in result.errors:
                self._highlight_field_error(field_id)
            self.set_status(result.first_error_message, is_error=True)
            first_err_field = next(iter(result.errors))
            self.field_entries[first_err_field].focus_set()

            error_details = "\n• " + "\n• ".join(result.errors.values())
            messagebox.showwarning(
                "Помилка заповнення форми",
                f"Не вдалося оновити товар. Перевірте поля форми:\n{error_details}",
                parent=self,
            )
            return

        updated_product = result.product
        assert updated_product is not None

        try:
            # Якщо користувач змінив ID, перестворюємо запис в сховищі
            if updated_product.id != self.selected_product_id:
                self.repository.delete(self.selected_product_id)
                self.repository.add(updated_product)
            else:
                self.repository.update(updated_product)

            self.selected_product_id = updated_product.id
            self.refresh_table()
            self._auto_save_if_possible()
            self.set_status(f"Товар '{updated_product.name}' (ID: {updated_product.id}) успішно оновлено та збережено.")
        except Exception as err:
            messagebox.showerror("Помилка оновлення", str(err), parent=self)
            self.set_status(str(err), is_error=True)

    def on_delete_product(self) -> None:
        """Видаляє обраний товар із підтвердженням у діалоговому вікні."""
        if not self.selected_product_id:
            messagebox.showinfo(
                "Увага",
                "Будь ласка, оберіть товар у таблиці для видалення.",
                parent=self,
            )
            self.set_status("Оберіть товар для видалення.", is_error=True)
            return

        product = self.repository.get_by_id(self.selected_product_id)
        if not product:
            return

        confirm = messagebox.askyesno(
            "Підтвердження видалення",
            f"Ви дійсно бажаєте видалити товар:\n\n"
            f"ID: {product.id}\n"
            f"Назва: {product.name}\n"
            f"Категорія: {product.category}\n\n"
            f"Цю дію неможливо скасувати.",
            icon="warning",
            parent=self,
        )

        if not confirm:
            return

        try:
            self.repository.delete(product.id)
            self.on_clear_form()
            self.refresh_table(keep_selection=False)
            self._auto_save_if_possible()
            self.set_status(f"Товар '{product.name}' (ID: {product.id}) видалено та зміни збережено.")
        except Exception as err:
            messagebox.showerror("Помилка видалення", str(err), parent=self)
            self.set_status(str(err), is_error=True)

    def _auto_save_if_possible(self) -> None:
        """
        Автоматично зберігає зміни у файл, щоб після перезапуску програми
        всі додані або змінені товари надійно зберігалися на диску.
        """
        try:
            current_path = getattr(self.repository, "current_filepath", None)
            if not current_path:
                current_path = os.path.abspath("inventory.csv")
                self.repository.current_filepath = current_path
            self.repository.save_to_file(current_path)
            self._update_window_title()
        except Exception as err:
            self.set_status(f"Попередження автозбереження: {err}", is_error=True)

    def on_clear_form(self) -> None:
        """Очищає форму та знімає виділення з таблиці."""
        self._clear_all_errors()
        self.selected_product_id = None
        for field_id in self.field_entries:
            self._set_field_value(field_id, "")
        self.lbl_created_at.config(text="Створено: —")
        self.tree.selection_remove(self.tree.selection())
        self.set_status("Форму очищено. Готово до додавання нового товару.")

    # -------------------------------------------------------------------------
    # Робота з файлами
    # -------------------------------------------------------------------------

    def _update_window_title(self) -> None:
        """Оновлює заголовок вікна залежно від відкритого файлу та наявності незбережених змін."""
        current_file = getattr(self.repository, "current_filepath", None)
        is_dirty = getattr(self.repository, "is_dirty", False)

        star = "*" if is_dirty else ""
        if current_file:
            fname = os.path.basename(current_file)
            self.title(f"Складський облік товарів — [{fname}{star}]")
        else:
            self.title(f"Складський облік товарів — [Новий список{star}]")

    def _prompt_save_changes_if_dirty(self) -> bool:
        """
        Перевіряє, чи є незбережені зміни.
        Повертає False, якщо користувач обрав 'Скасувати', інакше True.
        """
        if not getattr(self.repository, "is_dirty", False):
            return True

        answer = messagebox.askyesnocancel(
            "Незбережені зміни",
            "У поточному списку товарів є незбережені зміни.\n"
            "Бажаєте зберегти їх перед продовженням?",
            parent=self,
        )

        if answer is None:
            # Скасувати операцію
            return False
        if answer is True:
            # Зберегти
            return self.on_file_save()
        # "Ні" — продовжувати без збереження
        return True

    def on_file_new(self) -> None:
        """Створює новий порожній список обліку."""
        if not self._prompt_save_changes_if_dirty():
            return

        self.repository.clear()
        self.on_clear_form()
        self.search_var.set("")
        self.refresh_table()
        self.set_status("Створено новий порожній список.")

    def on_file_open(self) -> None:
        """Відкриває та завантажує дані з CSV-файлу."""
        if not self._prompt_save_changes_if_dirty():
            return

        filepath = filedialog.askopenfilename(
            parent=self,
            title="Відкрити файл обліку товарів",
            filetypes=[("Файли CSV", "*.csv"), ("Усі файли", "*.*")],
        )

        if not filepath:
            return

        try:
            count = self.repository.load_from_file(filepath)
            self.on_clear_form()
            self.search_var.set("")
            self.refresh_table()
            self.set_status(f"Успішно завантажено {count} товарів із файлу '{os.path.basename(filepath)}'.")
        except StorageFormatError as err:
            messagebox.showerror(
                "Помилка формату файлу",
                f"Файл має некоректний формат або заголовки:\n\n{err}",
                parent=self,
            )
            self.set_status("Помилка формату файлу.", is_error=True)
        except StorageError as err:
            messagebox.showerror(
                "Помилка відкриття файлу",
                f"Не вдалося відкрити файл:\n\n{err}",
                parent=self,
            )
            self.set_status("Не вдалося відкрити файл.", is_error=True)
        except Exception as err:
            messagebox.showerror(
                "Непередбачена помилка",
                f"Виникла помилка під час читання файлу:\n\n{err}",
                parent=self,
            )
            self.set_status(f"Помилка: {err}", is_error=True)

    def on_file_save(self) -> bool:
        """Зберігає дані у поточний відкритий файл або викликає 'Зберегти як'."""
        current_file = getattr(self.repository, "current_filepath", None)
        if not current_file:
            return self.on_file_save_as()

        try:
            count = self.repository.save_to_file(current_file)
            self._update_window_title()
            self.set_status(f"Успішно збережено {count} товарів у '{os.path.basename(current_file)}'.")
            return True
        except StorageError as err:
            messagebox.showerror(
                "Помилка збереження",
                f"Не вдалося зберегти файл:\n\n{err}",
                parent=self,
            )
            self.set_status("Помилка збереження файлу.", is_error=True)
            return False

    def on_file_save_as(self) -> bool:
        """Зберігає дані у новий вибраний користувачем файл."""
        initial_file = getattr(self.repository, "current_filepath", None) or "products.csv"
        initial_dir = os.path.dirname(initial_file) if initial_file else ""

        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Зберегти файл обліку як...",
            defaultextension=".csv",
            initialdir=initial_dir,
            initialfile=os.path.basename(initial_file),
            filetypes=[("Файли CSV", "*.csv"), ("Усі файли", "*.*")],
        )

        if not filepath:
            return False

        try:
            count = self.repository.save_to_file(filepath)
            self._update_window_title()
            self.set_status(f"Дані успішно збережено ({count} записів) у '{os.path.basename(filepath)}'.")
            return True
        except StorageError as err:
            messagebox.showerror(
                "Помилка збереження",
                f"Не вдалося зберегти файл:\n\n{err}",
                parent=self,
            )
            self.set_status("Помилка збереження файлу.", is_error=True)
            return False

    def on_close(self) -> None:
        """Обробник закриття програми: запит на збереження при наявності незбережених змін."""
        if not self._prompt_save_changes_if_dirty():
            return
        self.destroy()

    # -------------------------------------------------------------------------
    # Довідка
    # -------------------------------------------------------------------------

    def _show_about(self) -> None:
        """Відображає вікно 'Про програму'."""
        messagebox.showinfo(
            "Про програму",
            "Складський облік товарів v1.0\n\n"
            "Легка та оптимізована десктопна система для відділу обліку.\n"
            "Працює на чистому Python без зовнішніх бібліотек.\n"
            "Збереження даних у форматі CSV (UTF-8-SIG).\n\n"
            "Гарячі клавіші:\n"
            "• Ctrl+N — Новий список\n"
            "• Ctrl+O — Відкрити файл\n"
            "• Ctrl+S — Зберегти файл\n"
            "• Ctrl+F — Швидкий пошук\n"
            "• Esc — Очистити пошук / форму\n"
            "• Del — Видалити обраний товар",
            parent=self,
        )

