def _get_diet_foods(user_profile):
    """Get food recommendations based on country cuisine, diet type, and preferences."""

    allergies = (user_profile.allergies or '').lower()
    disliked = (user_profile.disliked_foods or '').lower()
    fav_foods_lower = (user_profile.favorite_foods or '').lower()

    # Get country name
    country_name = ''
    if user_profile.country:
        try:
            country_obj = pycountry.countries.get(alpha_2=user_profile.country)
            if country_obj:
                country_name = country_obj.name
        except:
            country_name = user_profile.country

    # Country-based cuisine mapping with meal items
    # Each country has meals organized by breakfast, lunch, dinner, snack
    cuisine_db = {
        'India': {
            'vegetarian': {
                'breakfast': ['Idli with sambar and coconut chutney', 'Masala dosa with sambar', 'Rava upma with coconut chutney', 'Aloo paratha with yogurt', 'Poha with peanuts'],
                'lunch': ['Rajma chawal (kidney beans with rice)', 'Chana masala with roti', 'Vegetable biryani with raita', 'Dal tadka with jeera rice', 'Palak paneer with naan'],
                'dinner': ['Aloo gobi with roti', 'Baingan bharta with rice', 'Mixed vegetable curry with dal', 'Kadhi pakora with rice', 'Vegetable korma with chapati'],
                'snack': ['Roasted chana', 'Masala peanuts', 'Fruit chaat', 'Sprouts salad', 'Dhokla']
            },
            'non_vegetarian': {
                'breakfast': ['Egg bhurji with toast', 'Masala omelette with paratha', 'Chicken keema with pav', 'Egg curry with appam', 'Mutton keema with roti'],
                'lunch': ['Chicken biryani with raita', 'Butter chicken with naan', 'Fish curry with rice', 'Mutton rogan josh with rice', 'Chicken tikka masala with roti'],
                'dinner': ['Tandoori chicken with naan', 'Fish fry with dal rice', 'Chicken chettinad with appam', 'Mutton curry with rice', 'Prawn masala with roti'],
                'snack': ['Chicken tikka', 'Seekh kebab', 'Egg pakora', 'Chicken 65', 'Mutton samosa']
            }
        },
        'United States': {
            'vegetarian': {
                'breakfast': ['Oatmeal with berries and nuts', 'Avocado toast with eggs', 'Greek yogurt parfait with granola', 'Vegetable omelette with toast', 'Smoothie bowl with spinach'],
                'lunch': ['Quinoa salad with chickpeas', 'Grilled vegetable sandwich', 'Lentil soup with bread', 'Buddha bowl with tofu', 'Caprese salad with quinoa'],
                'dinner': ['Vegetable stir-fry with brown rice', 'Black bean tacos', 'Vegetable lasagna', 'Stuffed bell peppers', 'Portobello mushroom burger'],
                'snack': ['Apple with almond butter', 'Hummus with veggies', 'Trail mix', 'Greek yogurt', 'Energy bars']
            },
            'non_vegetarian': {
                'breakfast': ['Scrambled eggs with bacon', 'Chicken sausage with toast', 'Turkey bacon with eggs', 'Protein pancakes', 'Breakfast burrito'],
                'lunch': ['Grilled chicken salad', 'Turkey club sandwich', 'Tuna salad sandwich', 'Chicken wrap', 'BBQ chicken sandwich'],
                'dinner': ['Grilled salmon with asparagus', 'Chicken breast with sweet potato', 'Lean beef with roasted vegetables', 'Turkey meatballs with pasta', 'Grilled chicken with quinoa'],
                'snack': ['Beef jerky', 'Hard boiled eggs', 'Protein shake', 'Turkey roll-ups', 'Chicken salad']
            }
        },
        'Mexico': {
            'vegetarian': {
                'breakfast': ['Chilaquiles with eggs', 'Huevos rancheros', 'Bean and cheese quesadilla', 'Avocado toast with salsa', 'Chilaquiles verdes'],
                'lunch': ['Bean burrito bowl', 'Vegetable quesadilla', 'Black bean tacos', 'Vegetarian enchiladas', 'Nopales salad'],
                'dinner': ['Vegetable enchiladas', 'Bean and cheese burritos', 'Vegetable fajitas', 'Chiles rellenos', 'Vegetable tamales'],
                'snack': ['Guacamole with chips', 'Roasted corn', 'Jicama with chili', 'Fresh fruit with tajin', 'Churros']
            },
            'non_vegetarian': {
                'breakfast': ['Chilaquiles with chicken', 'Huevos rancheros with chorizo', 'Breakfast tacos', 'Machaca con huevo', 'Chilaquiles rojos'],
                'lunch': ['Chicken tacos', 'Carne asada burrito', 'Chicken quesadilla', 'Beef enchiladas', 'Carnitas bowl'],
                'dinner': ['Chicken mole', 'Carne asada with rice', 'Fish tacos', 'Chicken enchiladas', 'Beef fajitas'],
                'snack': ['Chicharrones', 'Beef jerky', 'Queso fundido', 'Chicken taquitos', 'Beef empanada']
            }
        },
        'Italy': {
            'vegetarian': {
                'breakfast': ['Cappuccino with cornetto', 'Frittata with vegetables', 'Ricotta toast with honey', 'Yogurt with granola', 'Panini with mozzarella'],
                'lunch': ['Pasta primavera', 'Margherita pizza', 'Risotto with vegetables', 'Pasta e fagioli', 'Caprese salad with bread'],
                'dinner': ['Eggplant parmigiana', 'Vegetable lasagna', 'Pasta with pesto', 'Ratatouille with polenta', 'Stuffed peppers'],
                'snack': ['Bruschetta', 'Olives', 'Cheese plate', 'Fruit', 'Gelato']
            },
            'non_vegetarian': {
                'breakfast': ['Prosciutto with melon', 'Eggs with prosciutto', 'Frittata with ham', 'Panini with salami', 'Cappuccino with pastry'],
                'lunch': ['Chicken parmigiana', 'Spaghetti carbonara', 'Chicken piccata', 'Beef bolognese', 'Prosciutto panini'],
                'dinner': ['Osso buco', 'Chicken marsala', 'Beef ragu', 'Saltimbocca', 'Grilled fish with lemon'],
                'snack': ['Prosciutto', 'Parmesan', 'Olives', 'Salami', 'Arancini']
            }
        },
        'Japan': {
            'vegetarian': {
                'breakfast': ['Miso soup with tofu', 'Rice with natto', 'Vegetable tamagoyaki', 'Grilled vegetables', 'Rice porridge'],
                'lunch': ['Vegetable sushi rolls', 'Vegetable tempura', 'Tofu donburi', 'Vegetable ramen', 'Inari sushi'],
                'dinner': ['Vegetable stir-fry with rice', 'Agedashi tofu', 'Vegetable curry rice', 'Grilled vegetables with rice', 'Miso eggplant'],
                'snack': ['Edamame', 'Mochi', 'Rice crackers', 'Fruit', 'Sweet potato']
            },
            'non_vegetarian': {
                'breakfast': ['Grilled salmon with rice', 'Tamagoyaki', 'Fish with miso soup', 'Natto with rice', 'Tamago kake gohan'],
                'lunch': ['Chicken teriyaki bowl', 'Salmon sushi', 'Beef gyudon', 'Chicken katsu', 'Unagi don'],
                'dinner': ['Grilled salmon', 'Chicken teriyaki', 'Beef sukiyaki', 'Tonkatsu', 'Miso black cod'],
                'snack': ['Yakitori', 'Fish cakes', 'Shrimp tempura', 'Onigiri', 'Karaage']
            }
        },
        'Thailand': {
            'vegetarian': {
                'breakfast': ['Rice porridge with vegetables', 'Sticky rice with mango', 'Vegetable spring rolls', 'Tofu scramble', 'Rice noodle soup'],
                'lunch': ['Pad thai with tofu', 'Green curry with vegetables', 'Papaya salad (no fish sauce)', 'Vegetable fried rice', 'Massaman curry with vegetables'],
                'dinner': ['Red curry with vegetables', 'Stir-fried vegetables', 'Pineapple fried rice', 'Vegetable pad see ew', 'Yellow curry with tofu'],
                'snack': ['Fresh spring rolls', 'Mango sticky rice', 'Banana fritters', 'Coconut ice cream', 'Roasted peanuts']
            },
            'non_vegetarian': {
                'breakfast': ['Khao tom with shrimp', 'Kai jeow (Thai omelette)', 'Rice porridge with pork', 'Grilled pork with rice', 'Khanom jeen'],
                'lunch': ['Pad thai with shrimp', 'Green curry chicken', 'Pad kra pao (basil chicken)', 'Tom yum goong', 'Massaman curry beef'],
                'dinner': ['Pad thai with chicken', 'Green curry beef', 'Grilled fish with herbs', 'Panang curry chicken', 'Stir-fried basil pork'],
                'snack': ['Satay chicken', 'Fish cakes', 'Spring rolls', 'Grilled pork skewers', 'Shrimp cakes']
            }
        },
        'China': {
            'vegetarian': {
                'breakfast': ['Congee with pickled vegetables', 'Steamed buns with vegetables', 'Soy milk with youtiao', 'Vegetable dumplings', 'Noodle soup'],
                'lunch': ['Mapo tofu (vegetarian)', 'Buddha delight', 'Vegetable fried rice', 'Stir-fried vegetables', 'Vegetable lo mein'],
                'dinner': ['Mapo tofu', 'Stir-fried bok choy', 'Vegetable fried rice', 'Braised eggplant', 'Vegetable dumplings'],
                'snack': ['Steamed buns', 'Spring rolls', 'Vegetable dumplings', 'Fruit', 'Mooncakes']
            },
            'non_vegetarian': {
                'breakfast': ['Congee with century egg', 'Steamed buns with pork', 'Soy milk with fried dough', 'Pork dumplings', 'Noodle soup with beef'],
                'lunch': ['Kung pao chicken', 'Sweet and sour pork', 'Beef with broccoli', 'Orange chicken', 'Mapo tofu with pork'],
                'dinner': ['Peking duck', 'Kung pao chicken', 'Sweet and sour fish', 'Beef with oyster sauce', 'Steamed fish with ginger'],
                'snack': ['Pork buns', 'Shrimp dumplings', 'Scallion pancakes', 'Chicken feet', 'Egg tarts']
            }
        },
    }

    # Get cuisine for country, fallback to international (US-style) if not found
    cuisine = cuisine_db.get(country_name, cuisine_db.get('United States', {}))
    
    # Get diet-specific foods
    diet_type = user_profile.diet_type or 'non_vegetarian'
    foods = cuisine.get(diet_type, cuisine.get('non_vegetarian', {}))

    # If country not found, use a generic international fallback
    if not foods:
        foods = {
            'breakfast': ['Oatmeal with fruit', 'Scrambled eggs with toast', 'Yogurt with granola'],
            'lunch': ['Grilled chicken salad', 'Vegetable wrap', 'Quinoa bowl'],
            'dinner': ['Grilled salmon with vegetables', 'Chicken with rice', 'Vegetable stir-fry'],
            'snack': ['Nuts', 'Fruit', 'Yogurt', 'Hummus with vegetables']
        }

    # Filter out disliked and allergenic foods
    filtered_foods = {}
    for meal_type, items in foods.items():
        filtered_foods[meal_type] = [
            item for item in items
            if item.lower() not in disliked and item.lower() not in allergies
        ]
        # Ensure we have at least some options
        if not filtered_foods[meal_type]:
            # Fallback generic items
            filtered_foods[meal_type] = [
                'Oatmeal with fruit', 'Scrambled eggs with toast', 'Yogurt with granola'
            ] if meal_type == 'breakfast' else [
                'Grilled chicken salad', 'Vegetable wrap', 'Quinoa bowl'
            ] if meal_type == 'lunch' else [
                'Grilled salmon with vegetables', 'Chicken with rice', 'Vegetable stir-fry'
            ] if meal_type == 'dinner' else [
                'Nuts', 'Fruit', 'Yogurt', 'Hummus with vegetables'
            ]

    return filtered_foods