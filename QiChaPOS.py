import win32print
import win32ui
from PIL import Image, ImageWin
from datetime import datetime
from flask import Flask, request, jsonify
from square.client import Client

app = Flask(__name__)

# --------------------- Global Variables & Dictionaries ---------------------

# Global order counter: each Square order (which may contain multiple drinks)
# gets a sequential order ID that is shared across its labels.
global_order_counter = 0

# Drink codes mapping for printing
drinkCodes = {
    #Base drinks
    'Fruit Tea': 'Fruit Tea',
    'Milk Tea': 'Milk Tea',
    'Fruit Milk Tea': 'Fruit Milk Tea',
    'Matcha Latte': 'mat lat',
    'Fresh Matcha Latte': 'MAT lat',

    #Favourites
    'Strawberry Matcha': 'Str Mat',
    'Brown sugar boba': 'BsB',

    #Flavours
    'Peach': 'Peach',
    'Mango': 'Mango',
    'Strawberry': 'Str',
    'Passionfruit': 'Pas',
    'Tropical': 'Trop',
    'Lemon': 'Lemon',
    'Lime': 'Lime',

    #Milk Flavours
    'Chocolate': 'Choc',
    'Caramel': 'Car',
    'Strawberry': 'Straw',
    ''

    #Alternatives
    'Oat Milk': 'Oat',
    'Fresh Milk': 'Fresh',
    'Honey': 'Honey',
    'Brown Sugar' : 'Bs',


    #Add-ins
    'Brownsugar': 'Bs',
    'Vanilla': 'Van',
    'Cream': 'Cream',
    'Whipped cream': 'whip',

    #Toppings
    'Boba': 'Boba',
    'Brown Sugar Boba': 'BsB',
    'Peach Popping Pearls': 'Pch p',
    'Mango Popping Pearls': 'Mgo p',
    'Strawberry Popping Pearls': 'Str p',
    'Coconut Jelly': 'CJ',
    'Fresh Fruit': 'Ff',
}

# Define sets for classification
SWEETENERS = {"honey", "regular", "brown sugar", "caramel"}
FLAVOUR_KEYWORDS = {"peach", "strawberry", "mango", "tropical", "lemon", "lime", "chocolate", "caramel", "vanilla", "coffee", "matcha", "fresh matcha"}
TOPPINGS = {"boba", "brownsugar boba", "peach popping pearls", "mango popping pearls", "strawberry popping pearls", "coconut jelly", "fresh fruit", "cream", "whipped cream"}
# --------------------- Square API & Data Processing ---------------------

# Initialize the Square client (update token and environment as needed)
square_client = Client(
    access_token='EAAAlwnQW-KKvDNDNw4hUaB42gKlfZJLtae8B64EvF68-XLsjALd0NitXreEfzl6',  # Replace with your actual token
    environment='production'
)

def get_order_details(ord_id):
    result = square_client.orders.retrieve_order(order_id=ord_id)
    if result.is_success():
        return result.body
    elif result.is_error():
        print("Error fetching order:", result.errors)
        return result.errors

def data_filter(order_data):
    """
    Processes the Square order data and returns a list of label dictionaries.
    Each label represents one drink (even if quantity > 1) and includes keys:
      - id           : A sequential order ID shared across all drinks in the order.
      - size         : The drink size (from the variation name).
      - drink        : The drink name.
      - flavours     : A list of flavour modifiers.
      - alternative  : A milk alternative (only 'oat milk' or 'fresh milk').
      - ice          : Modifier from items ending with ' ice' (e.g., "extra ice").
      - sweetness    : Modifier from items ending with ' sweetner' (e.g., "less sweetner").
      - sweetener    : sweetner type
      - toppings     : A list of other modifiers (e.g., popping pearls, notes, etc.).
      - notes        : Combined notes from the order line and any modifiers.
    """
    global global_order_counter
    extracted_labels = []
    order_info = order_data.get("order", {})

    # Use a sequential order number for this Square order
    this_order_id = str(global_order_counter)
    global_order_counter += 1

    line_items = order_info.get("line_items", [])
    for item in line_items:
        item_name = item.get("name", "").strip()
        variation_name = item.get("variation_name", "").strip()
        note = item.get("note", "").strip()
        modifiers = [mod.get("name", "").strip() for mod in item.get("modifiers", [])]
        try:
            quantity = int(item.get("quantity", "1"))
        except ValueError:
            quantity = 1

        # Each unit (even if quantity > 1) gets its own label
        for _ in range(quantity):
            ice = ""
            sweetness = ""
            flavours = []
            alternative = ""
            sweetener = ""
            toppings = []
            extra_notes = []

            for m in modifiers:
                m_clean = m.strip()
                lower_m = m_clean.lower()
                # Process ice: e.g. "extra ice"
                if lower_m.endswith(" ice"):
                    value = m_clean[:-len(" ice")].strip()
                    if value:
                        ice = value.capitalize()
                    continue
                # Process sweetner: e.g. "less sweetness"
                elif lower_m.endswith(" sweetness"):
                    value = m_clean[:-len(" sweetness")].strip()
                    if value:
                        sweetness = value.capitalize()
                    continue
                # Process milk alternatives
                elif lower_m.endswith(" milk"):
                    value = m_clean[:-len(" milk")].strip()
                    if value:
                        alternative = value.capitalize()
                    continue
                # Process flavour keywords
                elif lower_m in SWEETENERS:
                    sweetener = m_clean
                elif lower_m in FLAVOUR_KEYWORDS:
                    flavours.append(m_clean)
                elif lower_m in TOPPINGS:
                    toppings.append(m_clean)
                else:
                    # Fallback: add any unclassified modifier to toppings
                    extra_notes.append(m_clean)

            # Combine the item's note with any extra notes from modifiers
            combined_notes = note
            if extra_notes:
                if combined_notes:
                    combined_notes += " " + " ".join(extra_notes)
                else:
                    combined_notes = " ".join(extra_notes)

            label = {
                "id": this_order_id,
                "size": variation_name,
                "drink": item_name,
                "flavours": flavours,
                "alternative": alternative,
                "ice": ice,
                "sweetness": sweetness,
                "sweetener": sweetener,
                "toppings": toppings,
                "notes": combined_notes
            }
            extracted_labels.append(label)

    return extracted_labels

# --------------------- Printing System ---------------------

def print_label(order):
    PADDING = 10
    printer_name = "MPT-II"  # Update to your printer's name
    hprinter = win32print.OpenPrinter(printer_name)
    printer_info = win32print.GetPrinter(hprinter, 2)
    print("Printer Status:", printer_info['Status'])

    image_path = "logo.png"  # Path to logo image
    try:
        image = Image.open(image_path)
        image = image.convert("RGB")
    except Exception as e:
        print("Error preparing image:", e)
        exit()

    pdc = win32ui.CreateDC()
    pdc.CreatePrinterDC(printer_name)
    pdc.StartDoc("Formatted Label")
    pdc.StartPage()

    titleFont = win32ui.CreateFont({
        "name": "Arial",
        "height": 42,
        "weight": 700,
    })
    font = win32ui.CreateFont({
        "name": "Arial",
        "height": 24,
        "weight": 400,
    })
    details_font = win32ui.CreateFont({
        "name": "Arial",
        "height": 24,
        "weight": 700,
    })
    separator_font = win32ui.CreateFont({
        "name": "Arial",
        "height": 8,
        "weight": 200,
    })

    pdc.SelectObject(titleFont)
    pdc.TextOut(PADDING + 10, 10, "QICHA BUBBLE TEA")

    try:
        width, height = 175, 88
        dib = ImageWin.Dib(image)
        x, y = 10, 50
        dib.draw(pdc.GetHandleOutput(), (PADDING + x, y, PADDING + x + width, y + height))
    except Exception as e:
        print("Error printing image:", e)

    pdc.SelectObject(separator_font)
    pdc.TextOut(PADDING + 10, 310, ".")

    # DETAILS PRINTING
    pdc.SelectObject(font)
    current_time = datetime.now()
    formatted_time = current_time.strftime("%H:%M - %d/%m/%Y")
    pdc.TextOut(PADDING + 10, 150, f"{formatted_time}")
    pdc.TextOut(PADDING + 10, 170, "ID:")
    pdc.SelectObject(details_font)
    pdc.TextOut(PADDING + 40, 170, f"{order['id']}")

    pdc.SelectObject(details_font)
    line1pt1 = f"{'Lrg' if order['size'].lower() == 'large' else 'Reg'}"
    pdc.TextOut(PADDING + 200, 48, line1pt1)
    pdc.SelectObject(font)
    drink_code = drinkCodes.get(order['drink'], order['drink'])
    line1pt2 = f"{drink_code}"
    pdc.TextOut(PADDING + 250, 48, line1pt2)

    # Line 2: Flavours
    line2 = ', '.join(drinkCodes.get(flavour, flavour) for flavour in order['flavours'])
    pdc.TextOut(PADDING + 200, 70, f"{line2}")

    # Line 3: Ice, Sweetness, Alternative
    line3 = ""
    for modifier in [order["ice"], order["sweetness"], order["alternative"], order['sweetener']]:
        if modifier in ['Regular', 'None', '']:
            line3 += "    "
        else:
            line3 += f"{drinkCodes.get(modifier, modifier)}   "
    pdc.TextOut(PADDING + 200, 92, f"{line3}")

    # Lines 4-6: Toppings
    line4, line5, line6 = "", "", ""
    for topping in order["toppings"]:
        code = drinkCodes.get(topping, topping)
        if len(line4 + code) < 16:
            line4 += code + "  "
        elif len(line5 + code) < 16:
            line5 += code + "  "
        else:
            line6 += code + "  "
    pdc.TextOut(PADDING + 200, 114, f"{line4}")
    pdc.TextOut(PADDING + 200, 136, f"{line5}")
    pdc.TextOut(PADDING + 200, 158, f"{line6}")

    # Line 7: Notes
    line7 = f"{order['notes']}"
    y_offset = 158 if line5 == "" else 180
    pdc.TextOut(PADDING + 200, y_offset, f"{line7}")

    pdc.EndPage()
    pdc.EndDoc()
    pdc.DeleteDC()

# --------------------- Webhook Listener ---------------------

@app.route('/webhook', methods=['POST'])
def webhook_listener():
    """Listen for Square order-created events and print labels for each drink."""
    data = request.json
    print("Received data:", data)

    if data and 'data' in data and 'id' in data['data']:
        order_id = data['data']['id']
        print(f"Order ID: {order_id}")

        order_details = get_order_details(order_id)
        print("Order Details:", order_details)

        filtered_labels = data_filter(order_details)
        print("Filtered Labels:", filtered_labels)

        # For each drink label in the order, print it.
        for label in filtered_labels:
            print("Printing label:", label)
            print_label(label)
    else:
        print("Invalid webhook payload.")

    # Acknowledge the webhook event
    return jsonify({'message': 'Webhook received'}), 200

# --------------------- Main Entry Point ---------------------

#ngrok http 5000 --url notable-locust-civil.ngrok-free.app 

if __name__ == '__main__':
    app.run(port=5000, debug=True)