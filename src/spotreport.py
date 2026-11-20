# Main File to run the Spot Report
import csv
import os
import random
import signal
import sys
import pygame
import time
import threading
import asyncio
from read import ex_menu_image, load_images, load_ans_files, input_args
from display import Button, Disp_Setup, menu_setup
from score import Score
from mouse import Mouse
from lsl_streams import read_lsl_inlet


# Ctrl+C, or the operator GUI closing this process (SIGTERM), ends it cleanly: the loops are
# left by an exception, the finally block in __main__ closes the window, and the LSL reader
# thread (a daemon) does not keep the process alive. The CSVs are appended to as events
# happen, so nothing already recorded is lost.
def _exit_on_signal(signum, frame):
    print(f"Spot report: received {signal.Signals(signum).name}, closing")
    sys.exit(0)


# Training Loop
def training_loop(training_imgs, training_dict, new_press):

    img_ID_training = 0 # index of the training image
    score = 0
    people_val, vehicle_val, bags_val, barrels_val, antennas_val = 0, 0, 0, 0, 0 # user counts
    obj_vals = [people_val, vehicle_val, bags_val, barrels_val, antennas_val]

    training_running = True
    mode = 0 # set mode to 0 to calculate score from correct dictionary

    while training_running:

        screen.fill('white')
        timer.tick(fps)
        file_extention = '' # file extention not needed since nothing is saved during training

        # Sets up all the add buttons
        add_button_list = Disp_Setup.add_buttons(args, screen)

        # Buttons only increase counts up to 5
        for i in range(len(add_button_list)):
            if add_button_list[i].check_click(new_press):
                new_press = False # reset to True in loop when mouse button is released
                if obj_vals[i] == 5:
                    continue
                else:
                    obj_vals[i] += 1

        # Sets up all the subtract buttons
        sub_button_list = Disp_Setup.subtract_buttons(args, screen)

        # Buttons only decrease counts down to 0
        for i in range(len(sub_button_list)):
            if sub_button_list[i].check_click(new_press):
                new_press = False # reset to True in loop when mouse button is released
                if obj_vals[i] == 0:
                    continue
                else:
                    obj_vals[i] -= 1

        # puts user counts of objects on the screen
        Disp_Setup.count_object_labels(args, screen, obj_vals)

        # Button for Next
        next_button = Button(args, screen, 'Next', args.next_xpos, args.next_ypos)

        # labels for target object types, 'score' and score value
        Disp_Setup.labels(args, screen, score)

        screen.blit(training_imgs[img_ID_training], (args.img_xpos, args.img_ypos)) # Display the current training image

        # When Next button is clicked, update the score and show next image
        if next_button.check_click(new_press):
            new_press = False # reset to True in loop when mouse button is released
            new_points = Score.calculate_score(args, img_ID_training, obj_vals, mode, score, training_dict, file_extention)
            score += new_points
            people_val, vehicle_val, bags_val, barrels_val, antennas_val = 0, 0, 0, 0, 0 # reset counts for next image
            obj_vals = [people_val, vehicle_val, bags_val, barrels_val, antennas_val]

            img_ID_training += 1 # increment the training img_ID
            #if last training image, exit the training loop
            if img_ID_training >= len(training_imgs):
                training_running = False
                return
            else:
                screen.blit(training_imgs[img_ID_training], (args.img_xpos, args.img_ypos)) # display the next image


        # Check if we want to exit training and if mouse button was released
        for event in pygame.event.get():
            # closing the window or pressing escape will exit training and take you back to the menu. can then hit escape again to quit.
            if event.type == pygame.QUIT:
                training_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    training_running = False
            if event.type == pygame.MOUSEBUTTONUP: # when a pressed mouse button is released
                new_press = True # the next mouse button press is a new press

        pygame.display.flip() # update the full display screen

    return

#loop for menu and task images loop
def loop(args, screen, task_imgs, training_imgs, task_dict, training_dict, new_press):

    menu_running = True
    SR_task_running = False

    # strings to hold subID and condition inputs; prefilled when the study launch passed
    # them (--subject-id / --condition), still editable in the boxes
    subID_text_input = preset_subject
    condition_text_input = preset_condition

    # rect objects to surround the user inputs
    # these are part of this loop to detect collisions for typing in the subID and condition inputs
    subID_rect = pygame.rect.Rect((140, 80), (140, 35)) # create rect object to surround subID_text_input
    condition_rect = pygame.rect.Rect((463, 80), (140, 35)) # create rect object to surround condition_text_input

    # boolean of whether the user inputs are active for typing
    active_subID_box = False
    active_condNo_box = False

    # 0 until training is done, 1 once Start is allowed. --skip-training starts at 1, so
    # Start works straight away (Training can still be run from the menu)
    mode = 1 if skip_training else 0
    start_task_time = 0 #timer for the time spent on each image

    # loop for the menu screen
    while menu_running:
        pygame.font.init() #initialize the font module
        screen.fill('gray94') #set background color
        timer.tick(fps)

        training_button, start_button = menu_setup(args, screen, ex_img, subID_text_input, condition_text_input, subID_rect, condition_rect)

        # enter the training_loop() if the training button is clicked
        if training_button.check_click(new_press):
            new_press = False # reset to True in loop when mouse button is released
            # before starting, make sure the textboxes were filled out
            if subID_text_input == '' or condition_text_input == '':
               print("Please fill in the Subject Id and Condition")
            else:
               training_loop(training_imgs, training_dict, new_press)
               mode = 1 # set the mode to 1 so the task loop can run now. can still do training again if desired.

        # Without training in between, nothing else has checked the ID boxes yet; empty ones
        # would name the output files "S_C.csv"
        if start_button.check_click(new_press) and mode == 1 and (subID_text_input == '' or condition_text_input == ''):
           new_press = False
           print("Please fill in the Subject Id and Condition")

        elif start_button.check_click(new_press) and mode == 1:
           new_press = False # reset to True in loop when mouse button is released
           menu_running = False
           SR_task_running = True # the only way to set this to True is by clicking Start
           start_task_time = time.time() # start the timer for the first image

        elif start_button.check_click(new_press) and mode == 0: # this code never seems to run, not sure why
           print("Please complete Training before progressing")
           new_press = False # reset to True in loop when mouse button is released

        for event in pygame.event.get():
            # stop running the menu loop if you close the window or press escape
            if event.type == pygame.QUIT:
                menu_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    menu_running = False
            if event.type == pygame.MOUSEBUTTONDOWN: # any mouse button is pressed
                if subID_rect.collidepoint(event.pos): # boolean of whether the event.pos (x,y) point is inside the rect object
                    active_subID_box = True # clicking on the subID_rect will make the text active for typing
                else:
                    active_subID_box = False # clicking anywhere else will make the text inactive for typing
                if condition_rect.collidepoint(event.pos):
                    active_condNo_box = True
                else:
                    active_condNo_box = False

            if event.type == pygame.KEYDOWN and active_subID_box: # if a key is pressed and the subID textbox is active
                if event.key == pygame.K_BACKSPACE: # if backspace is pressed, remove the last character
                    subID_text_input = subID_text_input[:-1]
                else:
                    subID_text_input += event.unicode # add the pressed character

            elif event.type == pygame.KEYDOWN and active_condNo_box:
                if event.key == pygame.K_BACKSPACE:
                    condition_text_input = condition_text_input[:-1]
                else:
                    condition_text_input += event.unicode

            elif event.type == pygame.MOUSEBUTTONUP: # when the pressed mouse button is released
                new_press = True # the next mouse button press is a new press

        pygame.display.flip() # update the full display screen

    # Closed from the menu (window X or Escape) without starting the task: there is nothing
    # to record, so leave before any output file is created. (Previously this fell through
    # and wrote empty "S_C.csv" headers, which crashed if the output folder was missing.)
    if not SR_task_running:
        return

    # task images loop
    # The task images are shown in a shuffled order. img_ID stays the image's real index
    # (what the answer key, scoring and every CSV use); pos is how far through the order we
    # are. Each pass through all the images gets a fresh order. --no-shuffle keeps 0, 1, 2...
    order_rng = random.Random(shuffle_seed)
    order_pass = 1

    def new_order():
        order = list(range(len(task_imgs)))
        if shuffle_images:
            order_rng.shuffle(order)
        return order

    order = new_order()
    pos = 0
    img_ID = order[pos] # index of the task image
    people_val, vehicle_val, bags_val, barrels_val, antennas_val = 0, 0, 0, 0, 0 # user counts of objects
    obj_vals = [people_val, vehicle_val, bags_val, barrels_val, antennas_val]
    score = 0
    lockout = 0 # boolean of whether the spot report is locked or not

    subtract_lockout = False # whether the spot report was locked and that time needs to be subtracted from the task time
    coming_from_lockout = False # whether the spot report is now unlocked coming from a locked state

    #set the extention for the output files based on the subID and condNo
    file_extention = 'S'+ subID_text_input + '_C' + condition_text_input + '.csv'

    # The order shown, one row per image per pass, so any run can be reconstructed
    order_path = os.path.join(getattr(args, 'output', '') or '.', 'image_order_' + file_extention)

    def write_order(order, pass_no):
        try:
            new = not os.path.exists(order_path)
            with open(order_path, 'a', newline='') as f:
                w = csv.writer(f)
                if new:
                    w.writerow(['pass', 'position', 'img_ID', 'seed', 'shuffled'])
                for i, idx in enumerate(order):
                    w.writerow([pass_no, i, idx, shuffle_seed, int(shuffle_images)])
        except Exception as e:
            print(f"Spot report: could not write the image order ({e})")

    write_order(order, order_pass)

    # write the headers for the output files
    Score.score_files_header(args, file_extention) # for both score and accuracy files
    Score.task_time_header(args, file_extention)
    Mouse.mouse_pos_header(args, file_extention)
    Mouse.mouse_button_header(args, file_extention)

    while SR_task_running:
        if not(lockout):
            if coming_from_lockout: #this is the first time the spot report is now unlocked coming from a locked state
                lockout_end_time = time.time() #the end time of the lockout
                coming_from_lockout = False
                subtract_lockout = True #true means we need to subtract the lockout time from the time spent on the image

            screen.fill('white')
            timer.tick(fps)

            # Sets up all the add buttons
            add_button_list = Disp_Setup.add_buttons(args, screen)

            # Buttons only increase counts up to 5
            for i in range(len(add_button_list)):
                if add_button_list[i].check_click(new_press):
                    new_press = False # reset to True in loop when mouse button is released
                    if obj_vals[i] == 5:
                        continue
                    else:
                        obj_vals[i] += 1

            # Sets up all the subtract buttons
            sub_button_list = Disp_Setup.subtract_buttons(args, screen)

            # Buttons only decrease counts down to 0
            for i in range(len(sub_button_list)):
                if sub_button_list[i].check_click(new_press):
                    new_press = False # reset to True in loop when mouse button is released
                    if obj_vals[i] == 0:
                        continue
                    else:
                        obj_vals[i] -= 1

            # puts user counts of objects on the screen
            Disp_Setup.count_object_labels(args, screen, obj_vals)

            # Button for Next
            next_button = Button(args, screen, 'Next', args.next_xpos, args.next_ypos)

            # labels for target object types, 'score' and score value
            Disp_Setup.labels(args, screen, score)

            screen.blit(task_imgs[img_ID], (args.img_xpos, args.img_ypos)) # Display the current task image

            # When Next button is clicked, update the score and show next image
            if next_button.check_click(new_press):
                end_task_time = time.time() #the end time for the current image
                new_press = False # reset to True in loop when mouse button is released
                new_points = Score.calculate_score(args, img_ID, obj_vals, mode, score, task_dict, file_extention)
                score += new_points
                people_val, vehicle_val, bags_val, barrels_val, antennas_val = 0, 0, 0, 0, 0 # reset counts for next image
                obj_vals = [people_val, vehicle_val, bags_val, barrels_val, antennas_val]

                if subtract_lockout:
                    task_time = (end_task_time - start_task_time) - (lockout_end_time - lockout_start_time)
                    subtract_lockout = False
                else:
                    task_time = end_task_time - start_task_time # calculate task time
                Score.write_task_time(args, img_ID, task_time, file_extention) # write to csv and send data to LSL
                start_task_time = end_task_time # set the end time as the starting time for the next image

                # next image in the order; after the last one, start a new pass in a new order
                pos += 1
                if pos >= len(order):
                    order_pass += 1
                    order = new_order()
                    write_order(order, order_pass)
                    pos = 0
                img_ID = order[pos]
                screen.blit(task_imgs[img_ID], (args.img_xpos, args.img_ypos)) # display the next image

        else: # spot report is locked
            screen.fill('black')
            font = pygame.font.SysFont(args.font_type, 150)
            locked_text = font.render('LOCKED', True, 'white')
            screen.blit(locked_text, (450, 300))

            if coming_from_lockout == False:
                lockout_start_time = time.time() # the time when the lockout started
                coming_from_lockout = True # when the spot report becomes unlocked, we will be coming from a lockout state

        # Event Loop
        for event in pygame.event.get(): # monitor user inputs
            if event.type == pygame.QUIT: # if X is clicked to close the window or escape is pressed, stop running the loop
                SR_task_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    SR_task_running = False
                if event.key == pygame.K_l: # if the 'L' key is pressed
                    lockout = True # spot report is locked
                if event.key == pygame.K_u: # if the 'U' key is pressed
                    lockout =  False # spot report is unlocked
            if event.type == pygame.MOUSEBUTTONUP: # when the pressed mouse button is released
                new_press = True # the next mouse button press is a new press
                Mouse.write_mouse_button(args, img_ID, "Released", file_extention) # write to csv and send data to LSL
            if event.type == pygame.MOUSEBUTTONDOWN: #when the mouse button is pressed
                Mouse.write_mouse_button(args, img_ID, "Pressed", file_extention) # write to csv and send data to LSL
            if event.type == pygame.MOUSEMOTION: #when the mouse cursor moves
                Mouse.write_mouse_pos(args, img_ID, event.pos, file_extention) # write to csv and send data to LSL

        pygame.display.flip() # update the full display screen

    return # pygame is closed by the finally block in __main__


async def start_asyncio_loop():
    # A separate thread for reading LSL data. Daemon, so it can never hold the process open
    # after the window closes: read_lsl_inlet waits on its stream indefinitely, and the old
    # join() here blocked forever whenever no LSL stream was present (or the loop crashed).
    lsl_thread = threading.Thread(target=read_lsl_inlet, daemon=True)
    lsl_thread.start() # start the thread

    # loop with menu, training, and task
    loop(args, screen, task_imgs, training_imgs, task_dict, training_dict, new_press)

    return


# Main Function
if __name__ == "__main__":

    signal.signal(signal.SIGINT, _exit_on_signal)
    signal.signal(signal.SIGTERM, _exit_on_signal)

    pygame.init() # initialize all imported modules, including font

    # Our own flag, taken off the command line before input_args() sees it
    skip_training = '--skip-training' in sys.argv
    if skip_training:
        sys.argv.remove('--skip-training')
        print("Spot report: training is optional this run (--skip-training)")

    # Subject ID and condition from the study launch, to prefill the menu's boxes. Also taken
    # off the command line first, so input_args() never sees options it does not know.
    def _take_option(name):
        if name in sys.argv:
            i = sys.argv.index(name)
            value = sys.argv[i + 1] if i + 1 < len(sys.argv) else ''
            del sys.argv[i:i + 2]
            return value
        return ''

    # Task image order: shuffled by default (--no-shuffle for the fixed order). The seed is
    # random unless --seed N is given, and is saved in image_order_*.csv either way.
    shuffle_images = '--no-shuffle' not in sys.argv
    if not shuffle_images:
        sys.argv.remove('--no-shuffle')
    seed_arg = _take_option('--seed')
    shuffle_seed = int(seed_arg) if seed_arg else random.SystemRandom().randrange(2**31)
    print(f"Spot report: task images {'shuffled, seed ' + str(shuffle_seed) if shuffle_images else 'in fixed order'}")

    preset_subject = _take_option('--subject-id')
    preset_condition = _take_option('--condition')
    if preset_subject or preset_condition:
        print(f"Spot report: subject '{preset_subject}', condition '{preset_condition}'")

    try:
        args = input_args() # optional arguments from user for design/device specifics (e.g., screen size)

        # The output folder is created if missing, rather than every CSV write failing in it
        out = getattr(args, 'output', None)
        if out:
            os.makedirs(out, exist_ok=True)
            print(f"Spot report output: {out}")

        screen = pygame.display.set_mode([args.width, args.height]) # display surface with screen width and height
        fps = 60
        timer = pygame.time.Clock() # clock object for keeping track of time

        font = pygame.font.SysFont(args.font_type, 1) # set the font type and size. Font size is different throughout and set as needed
        pygame.display.set_caption("Spot Report") # name of the window caption

        new_press = True # if the next mouse click is a new press

        # read in the answer keys
        training_dict, task_dict = load_ans_files(args)

        # read in the training images
        training_imgs = load_images(args, key="train")

        # read in the task images
        task_imgs = load_images(args, key="task",noOfImages=250)

        # read in the example objects for the menu
        ex_img = ex_menu_image(args)

        asyncio.run(start_asyncio_loop()) #start LSL and main loop

    finally:
        # Whatever ended the run (finished, closed, Escape, a signal or an error), the window
        # goes away; an error's traceback still prints after this
        pygame.quit()
