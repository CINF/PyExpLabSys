def run():
    """The main part of the program"""
    select = None
    data = {}
    picaso.text_foreground_color((1, 1, 1))
    while select != 'q':
        #message = "Enter (e)dit, (b)uy or (q)uit and press enter: "
        #select = raw_input(message)
        select = 'b'
        if select == 'b':
            try:
                picaso.clear_screen()
                picaso.put_string("Welcome to the Friday Bar!")
                picaso.move_cursor(1, 0)
                picaso.put_string("Friday Bar System Version {}".format(__version__))
                picaso.move_cursor(4, 0)
                picaso.put_string('Scan your barcode!')
                data['barcode'] = read_barcode()
                #print cowsay('Special price for you my friend (in DKK): \n' + str(bc.get_item(data['barcode'], statement='price')))
                picaso.clear_screen()
                #picaso.put_string('Special price for you my friend: \n' + str(bc.get_item(data['barcode'], statement='price')) + ' DKK')
                try:
                    picaso.put_string(cowsay('Special price for you my friend: \n' + str(bc.get_item(data['barcode'], statement='price')) + ' DKK'))
                except:
                    picaso.put_string(cowsay('Invalid barcode! Are you drunk?'))
                    time.sleep(3)
                    continue
                time.sleep(3)
                picaso.clear_screen()
                #os.system('clear')
                name = bc.get_item(data['barcode'], statement='name').decode('utf-8')
                picaso.put_string(cowsay('Enjoy your delicious ' + to_ascii(name)))
                time.sleep(2)
                #time.sleep(3)
                #os.system('clear')
            except IOError:##ValueError:
                print 'Wrong input!... are you drunk?'
                return
        elif select == 'u':
            update()

