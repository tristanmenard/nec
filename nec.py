import numpy as np
import os
import subprocess
import re
import time
import webbrowser

def open_necfile(necfilename):
    op = subprocess.Popen(['notepad.exe', necfilename])

def help(necdoc="file:///C:/4nec2/Nec4UsersMan.pdf"):
    op = webbrowser.get("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s").open(necdoc)

def check_str_deg2rad_conversion(string, starter=['cos(', 'sin(', 'tan(']):
    for outer_func in starter:
        offset = len(outer_func)
        for i in range(len(string)):
            if string[i:i+offset] == outer_func:
                if string[i-3:i] != 'np.':
                    raise Exception('String conversion error.')


def convert_str_deg2rad(string, starter=['cos(', 'sin(', 'tan(']):
    factor = '0.0174532925' # multiplication factor for conversion from deg to rad (=pi/180)
    string = string+' '*len(string) # pad string with whitespaces to that trig terms near the end of the string don't get cut off
    for outer_func in starter:
        offset = len(outer_func)
        for i in range(len(string)):
            if string[i:i+offset] == outer_func:
                if string[i-3:i] == 'np.':
                    continue
                else:
                    c = 1
                    for j in range(i+offset,len(string)):
                        if string[j] == '(':
                            c += 1
                        if string[j] == ')':
                            c -= 1
                            if c == 0:
                                string = string[:i]+'np.'+string[i:i+offset]+'('+string[i+offset:j]+')*'+factor+string[j:]
                                break
    check_str_deg2rad_conversion(string, starter) # check for errors
    return string.rstrip() # remove extra whitespaces



def replace_variable_in_string(string, variable, value):
    split_string = re.split('(\W)', string)
    for i in range(len(split_string)):
        for j in range(len(variable)):
            if split_string[i] == variable[j]:
                split_string[i] = value[j]
    new_string = convert_str_deg2rad(''.join(split_string)).split()
    for k in range(len(new_string)):
        try:
            new_string[k] = str(eval(new_string[k]))
        except:
            continue
    return ' '.join(new_string)



def convert_nec2inp(necfilename, inputfilename=[], verbose=False):
    if not inputfilename:
        inputfilename = necfilename.replace('_', '').replace('.nec', '.inp')

    with open(necfilename, 'r') as necfile, open(inputfilename, 'w') as inputfile:
        for line in necfile:
            line = line.replace('\t', ' ')
            line_with_comment = re.search('^(.+)\s+\'', line)
            if line_with_comment:
                inputfile.write(line_with_comment.group(1)+'\n')
            else:
                inputfile.write(line)

    with open(inputfilename, 'r') as inputfile:
        file = inputfile.read()

    symbol = []
    value = []
    all_lines = file.split('\n')
    for line in all_lines:
        SY = re.match('^SY\s(\S+)=(\S+)', line)
        if SY:
            symbol.append(SY.group(1))
            value.append(SY.group(2))

    value_line_str = replace_variable_in_string(' '.join(value), symbol, value)
    value_list_str = value_line_str.split()

    with open('temp.inp', 'w') as tempfile:
        for line in all_lines:
            if not line.startswith('SY'):
                converted_line = replace_variable_in_string(line, symbol, value_list_str)
                tempfile.write(converted_line+'\n')

    # Replace the INPUT file with the new version that doesn't have SY cards.
    os.remove(inputfilename)
    os.rename('temp.inp', inputfilename)
    if verbose:
        print('Converted '+necfilename+' to '+'inputfilename')



def run_nec_exe(nec_exe, inputfile, outputfile=[]):
    if not outputfile:
        outputfile = inputfile.replace('.inp', '.out')
    # Run the NEC .exe application from the command line, then enter the .inp and .out file locations.
    run = subprocess.call([nec_exe, inputfile, outputfile]) # subprocess.call runs the .exe from the command line and waits for the process to finish



def get_data(filename, tempfilename='temp_data.txt'):
    with open(filename, 'r') as file, open(tempfilename, 'w') as tempfile:
        tempfile.write('Frequency [MHz]\tTheta [deg]\tPhi [deg]\tCurrent mag. [A]\tCurrent phase [deg]\n')
        match_I = False
        for line in file:
            # 1) Find frequency
            match_freq = re.search('FREQUENCY=\s+(\S+)', line)
            if match_freq:
                freq = match_freq.group(1)
            # 2) Find Receiving pattern parameters
            if re.search('RECEIVING PATTERN PARAMETERS', line):
                match_I = True
                continue
            elif match_I:
                try:
                    data = [float(num) for num in line.split()]
                    tempfile.write(str(float(freq))+'\t\t\t\t'+str(data[0])+'\t\t'+str(data[1])+'\t\t\t'+str(data[2])+'\t\t\t'+str(data[3])+'\n')
                except:
                    continue


def calculate(nec_exe, necfile, inputfile=[], outputfile=[], tempfile=r'.\out\temp_data.txt', out_folder='\\out\\'):
    path, file = necfile.rsplit('\\', 1)
    if not inputfile:
        inputfile = path+out_folder+file.replace('_','').replace(' ','').replace('.nec','.inp')
    if not outputfile:
        outputfile = inputfile.replace('.inp', '.out')

    # Convert the .nec file to a .inp file that is appropriate for us by the NEC exe.
    convert_nec2inp(necfile, inputfile)
    # Run the NEC exe that returns a .out file with the receiving pattern information.
    run_nec_exe(nec_exe, inputfile, outputfile)
    # Create a temporary file to organize the simulation data in the .out file.
    get_data(outputfile, tempfile)
    # Load the data that is contained in the .out file.
    freq, theta, phi, I_mag, I_phase = np.loadtxt(tempfile, skiprows=1, unpack=True)
    return freq, theta, phi, I_mag, I_phase



def sweep(nec_exe, necfilename, sweep_parameter, sweep_values, inputfile=[], outputfile=[], out_folder=[], tempfilename=[], sweep_name=[], datafile=[]):
    path, filename = necfilename.rsplit('\\',1)
    if not out_folder:
        out_folder = path+'\\out\\'
    # Make folder to hold sweep results.
    if not sweep_name:
        sweep_name = sweep_parameter+'Sweep'
    if not os.path.isdir(out_folder+sweep_name):
        os.mkdir(out_folder+sweep_name)

    if not inputfile:
        # path\out\sweep_name\filename.inp
        inputfile = out_folder+sweep_name+'\\'+filename.replace('_','').replace(' ','').replace('.nec','.inp')
    if not outputfile:
        # path\out\sweep_name\filename.out
        outputfile = inputfile.replace('.inp', '.out')
    if not tempfilename:
        # path\out\sweep_name\tempsweep.nec
        tempfilename = out_folder+sweep_name+'\\tempsweep.nec'
    if not datafile:
        #path\out\sweep_name\sweep_results.txt
        datafile = out_folder+sweep_name+'\\sweep_results.txt'

    # Read the original .nec file.
    with open(necfilename, 'r') as necfile:
        file = necfile.read()
    all_lines = file.split('\n')

    with open(datafile, 'w') as newfile:
        newfile.write('Parameter ('+sweep_parameter+') value\tFrequency [MHz]\tTheta [deg]\tPhi [deg]\tCurrent mag. [A]\tCurrent phase [deg]\n')
        # Write modified .nec files to a temporary file for each sweep value.
        for i in range(len(sweep_values)):
            with open(tempfilename, 'w') as tempfile:
                # Find the SY card that defines the value of the sweep parameter.
                for line in all_lines:
                    SY = re.match('^SY\s+(\S+)=(\S+)', line)
                    if SY:
                        if SY.group(1) == sweep_parameter:
                            # Replace the value of the sweep parameter with the desired sweep parameter value.
                            line = re.sub(SY.group(2), str(sweep_values[i]), line)
                            tempfile.write(line+'\n')
                        else:
                            tempfile.write(line+'\n')
                    else:
                        tempfile.write(line+'\n')
            # Close the temporary file and use its contents to complete a NEC simulation.
            convert_nec2inp(tempfilename, inputfile) # convert .nec files to .inp files
            run_nec_exe(nec_exe, inputfile, outputfile) # run .inp files in NEC4 .exe --> returns .out silmulation result files

            # Rename the .inp and .out files for each sweep value.
            new_inputfile = ('_sweep_'+sweep_parameter+'_'+str(sweep_values[i]).replace('.','_')+'.').join(inputfile.rsplit('.',1))
            if os.path.exists(new_inputfile):
                print('Overwriting previous results: '+new_inputfile)
                os.remove(new_inputfile)
            os.rename(inputfile, new_inputfile)

            new_outputfile = ('_sweep_'+sweep_parameter+'_'+str(sweep_values[i]).replace('.','_')+'.').join(outputfile.rsplit('.',1))
            if os.path.exists(new_outputfile):
                print('Overwriting previous results: '+new_outputfile)
                os.remove(new_outputfile)
            os.rename(outputfile, new_outputfile)

            # Get the data from each .out file...
            # Write the cumulative simulation results to a text file.
            with open(new_outputfile, 'r') as outfile:
                match_I = False
                for line in outfile:
                    # 1) Find frequency
                    match_freq = re.search('FREQUENCY=\s+(\S+)', line)
                    if match_freq:
                        freq = match_freq.group(1)
                    # 2) Find Receiving pattern parameters
                    if re.search('RECEIVING PATTERN PARAMETERS', line):
                        match_I = True
                        continue
                    elif match_I:
                        try:
                            data = [float(num) for num in line.split()]
                            newfile.write(str(sweep_values[i])+'\t'+str(float(freq))+'\t'+str(data[0])+'\t'+str(data[1])+'\t'+str(data[2])+'\t'+str(data[3])+'\n')
                        except:
                            continue

    par_value, freq_value, theta, phi, I_mag, I_phase = np.loadtxt(datafile, skiprows=1, unpack=True)
    return par_value, freq_value, theta, phi, I_mag, I_phase



def replace_line(card, new_string, necfilename, tempfilename='temp.nec', newfilename=[]):
    if card == 'GW' or card == 'LD':
        raise Exception('Must specify tag number. Format: "GW\t1" (separated by tab)')
    if card.startswith('SY'):
        if card == 'SY':
            raise Exception('Must specify variable name. Format: "SY a=" where "a" is the variable name.')
        elif card[-1] != '=':
            raise Exception('Must specify end of variable name with "=". Format: "SY a=" where "a" is the variable name.')
    if new_string[-1] != '\n':
        raise Exception('Missing end of line character "\\n".')

    with open(necfilename, 'r') as oldfile, open(tempfilename, 'w') as tempfile:
        for line in oldfile:
            if line.startswith(card):
                tempfile.write(new_string)
            else:
                tempfile.write(line)

    if not newfilename:
        newfilename = necfilename
        os.remove(necfilename)
    os.rename(tempfilename, newfilename)
