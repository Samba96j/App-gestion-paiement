class Paginator:
    def __init__(self, items, page_size=10):
        self.items = items
        self.page_size = page_size
        self.total_pages = (len(items) + page_size - 1) // page_size
    
    def get_page(self, page_number):
        start = (page_number - 1) * self.page_size
        end = start + self.page_size
        return self.items[start:end]