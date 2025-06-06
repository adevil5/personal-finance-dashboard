"""
Default categories for new users.

This module defines the default category structure that will be created
for new users when they register or when existing users request default categories.
"""

DEFAULT_CATEGORIES = [
    {
        "name": "Food & Dining",
        "color": "#E74C3C",
        "icon": "utensils",
        "children": [
            {"name": "Groceries", "color": "#E74C3C", "icon": "shopping-cart"},
            {"name": "Restaurants", "color": "#E74C3C", "icon": "store"},
            {"name": "Fast Food", "color": "#E74C3C", "icon": "hamburger"},
            {"name": "Coffee Shops", "color": "#E74C3C", "icon": "coffee"},
        ],
    },
    {
        "name": "Transportation",
        "color": "#3498DB",
        "icon": "car",
        "children": [
            {"name": "Gas & Fuel", "color": "#3498DB", "icon": "gas-pump"},
            {"name": "Public Transit", "color": "#3498DB", "icon": "bus"},
            {"name": "Parking", "color": "#3498DB", "icon": "parking"},
            {"name": "Car Maintenance", "color": "#3498DB", "icon": "wrench"},
            {"name": "Rideshare", "color": "#3498DB", "icon": "taxi"},
        ],
    },
    {
        "name": "Shopping",
        "color": "#9B59B6",
        "icon": "shopping-bag",
        "children": [
            {"name": "Clothing", "color": "#9B59B6", "icon": "tshirt"},
            {"name": "Electronics", "color": "#9B59B6", "icon": "laptop"},
            {"name": "Books", "color": "#9B59B6", "icon": "book"},
            {"name": "General Merchandise", "color": "#9B59B6", "icon": "gift"},
        ],
    },
    {
        "name": "Bills & Utilities",
        "color": "#F39C12",
        "icon": "file-invoice",
        "children": [
            {"name": "Rent/Mortgage", "color": "#F39C12", "icon": "home"},
            {"name": "Electricity", "color": "#F39C12", "icon": "bolt"},
            {"name": "Water", "color": "#F39C12", "icon": "tint"},
            {"name": "Internet", "color": "#F39C12", "icon": "wifi"},
            {"name": "Phone", "color": "#F39C12", "icon": "phone"},
            {"name": "Insurance", "color": "#F39C12", "icon": "shield-alt"},
        ],
    },
    {
        "name": "Entertainment",
        "color": "#E67E22",
        "icon": "gamepad",
        "children": [
            {"name": "Movies", "color": "#E67E22", "icon": "film"},
            {"name": "Music & Streaming", "color": "#E67E22", "icon": "music"},
            {"name": "Sports", "color": "#E67E22", "icon": "football-ball"},
            {"name": "Hobbies", "color": "#E67E22", "icon": "palette"},
        ],
    },
    {
        "name": "Healthcare",
        "color": "#1ABC9C",
        "icon": "heartbeat",
        "children": [
            {"name": "Doctor Visits", "color": "#1ABC9C", "icon": "stethoscope"},
            {"name": "Pharmacy", "color": "#1ABC9C", "icon": "pills"},
            {"name": "Dental", "color": "#1ABC9C", "icon": "tooth"},
            {"name": "Vision", "color": "#1ABC9C", "icon": "eye"},
        ],
    },
    {
        "name": "Personal Care",
        "color": "#F1C40F",
        "icon": "spa",
        "children": [
            {"name": "Haircuts", "color": "#F1C40F", "icon": "cut"},
            {"name": "Cosmetics", "color": "#F1C40F", "icon": "kiss"},
            {"name": "Gym & Fitness", "color": "#F1C40F", "icon": "dumbbell"},
        ],
    },
    {
        "name": "Travel",
        "color": "#16A085",
        "icon": "plane",
        "children": [
            {"name": "Flights", "color": "#16A085", "icon": "plane-departure"},
            {"name": "Hotels", "color": "#16A085", "icon": "bed"},
            {"name": "Activities", "color": "#16A085", "icon": "map-marked-alt"},
        ],
    },
    {
        "name": "Education",
        "color": "#8E44AD",
        "icon": "graduation-cap",
        "children": [
            {"name": "Tuition", "color": "#8E44AD", "icon": "university"},
            {"name": "Books & Supplies", "color": "#8E44AD", "icon": "book-open"},
            {"name": "Courses", "color": "#8E44AD", "icon": "chalkboard"},
        ],
    },
    {
        "name": "Home & Garden",
        "color": "#27AE60",
        "icon": "home",
        "children": [
            {"name": "Furniture", "color": "#27AE60", "icon": "couch"},
            {"name": "Appliances", "color": "#27AE60", "icon": "blender"},
            {"name": "Gardening", "color": "#27AE60", "icon": "seedling"},
            {"name": "Home Improvement", "color": "#27AE60", "icon": "hammer"},
        ],
    },
    {
        "name": "Gifts & Donations",
        "color": "#E91E63",
        "icon": "gift",
        "children": [
            {"name": "Gifts", "color": "#E91E63", "icon": "gift"},
            {"name": "Charity", "color": "#E91E63", "icon": "heart"},
            {"name": "Religious", "color": "#E91E63", "icon": "pray"},
        ],
    },
    {
        "name": "Business",
        "color": "#34495E",
        "icon": "briefcase",
        "children": [
            {"name": "Office Supplies", "color": "#34495E", "icon": "paperclip"},
            {"name": "Professional Services", "color": "#34495E", "icon": "handshake"},
            {"name": "Business Travel", "color": "#34495E", "icon": "suitcase"},
        ],
    },
    {
        "name": "Income",
        "color": "#2ECC71",
        "icon": "dollar-sign",
        "children": [
            {"name": "Salary", "color": "#2ECC71", "icon": "money-check"},
            {"name": "Freelance", "color": "#2ECC71", "icon": "laptop-code"},
            {"name": "Investments", "color": "#2ECC71", "icon": "chart-line"},
            {"name": "Other Income", "color": "#2ECC71", "icon": "coins"},
        ],
    },
    {
        "name": "Miscellaneous",
        "color": "#95A5A6",
        "icon": "ellipsis-h",
        "children": [
            {"name": "Bank Fees", "color": "#95A5A6", "icon": "university"},
            {"name": "Taxes", "color": "#95A5A6", "icon": "file-invoice-dollar"},
            {"name": "Other", "color": "#95A5A6", "icon": "question"},
        ],
    },
]
