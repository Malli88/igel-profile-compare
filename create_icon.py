"""Create a simple icon file."""
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (256, 256), (0, 120, 200, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 236, 236], outline='white', width=8)
    draw.text((60, 90), 'IPM', fill='white')
    img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print('Icon created: icon.ico')
except ImportError:
    print('Pillow not installed - using default icon')
    # Create minimal ICO file
    ico_data = bytes([0,0,1,0,1,0,16,16,0,0,1,0,32,0,104,4,0,0,22,0,0,0]) + bytes(1128)
    with open('icon.ico', 'wb') as f:
        f.write(ico_data)
