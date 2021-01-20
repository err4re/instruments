from instruments import mcdc2805
import importlib
importlib.reload(mcdc2805)
import pyvisa as visa
try:
    moteur = mcdc2805.Mcdc2805("ASRL1::INSTR")
    print("======================")

    # read some communication parameter
    p1 = moteur.visa_instr.baud_rate
    p2 = moteur.visa_instr.parity
    p3 = moteur.visa_instr.stop_bits
    p4 = moteur.visa_instr.data_bits
    print("Back end Baud rate = "+str(p1))
    print("Back end Parity = "+str(p2))
    print("Back end Stop bits = "+str(p3))
    print("Back end Data bits = "+str(p4))
    
    resolution = moteur.encoder_resolution()
    print("old resolution : "+str(resolution))
    # new_res = 2048
    # moteur.encoder_resolution(new_res)
    # resolution = moteur.encoder_resolution()
    # print("new resolution : "+str(resolution))

    # # initialise motor
    # initial_accele = 10
    # moteur.acceleration(initial_accele)
    # max_speed = 60
    # moteur.max_vel(max_speed)
    # moteur.set_position_mode()


    speed = moteur.velocity()
    print("Speed : " + str(speed) + " rpm")

    # moteur.save_config_at_start()

    # #test sequence
    # moteur.rotate_to(100)
    # moteur.acceleration(2)
    # moteur.notify_vel(60)
    # moteur.motion_start()





finally:
    #close 
    del moteur
    print("======================")
    print ("End of process")
    # print ("Write next command")