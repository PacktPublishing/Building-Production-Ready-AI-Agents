import sqlite3


conn = sqlite3.connect('products.db')
cursor = conn.cursor()

cursor.execute(
    '''CREATE TABLE IF NOT EXISTS products
             (id INTEGER PRIMARY KEY, name TEXT, price REAL)'''
)

products = [
    (1, 'Laptop', 999.99),
    (2, 'Smartphone', 499.99),
    (3, 'Tablet', 299.99),
]

cursor.executemany('INSERT OR IGNORE INTO products VALUES (?, ?, ?)', products)
conn.commit()


def get_products(max_price: float | None = None):
    """
    Fetches a list of products from the database, optionally filtered by price.

    Args:
      max_price: Optional max price filter.

    Returns:
      list: A list of product names with prices if the request is successful, otherwise a list with an error message.
    """
    if max_price is None:
        cursor.execute('SELECT name, price FROM products')
    else:
        cursor.execute('SELECT name, price FROM products WHERE price <= ?', (max_price,))

    data = cursor.fetchall()
    if data:
        return [f"{product[0]} (${product[1]})" for product in data]
    return ['Unable to fetch data']
