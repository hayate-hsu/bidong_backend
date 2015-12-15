import os
import sys

# insert current path's parent to system path
# parent = os.path.abspath(os.path.pardir)
# print(parent)
sys.path.insert(0, os.path.abspath(os.path.pardir))

import account

def main(path):
    '''
    '''
    with open(path, 'rb') as f:
        for line in f:
            # print(line)
            line = line.strip()
            items = line.split(',')
            record = {'name':items[1], 'mobile':items[4]}
            if items[2]:
                record['position'] = items[2]
            if items[3]:
                record['phone'] = items[3]
            print('No:{}, value:{}'.format(items[0], record))
            account.add_ns_employee(**record)


if __name__ == '__main__':
    current = os.path.abspath(os.path.dirname(__file__))
    main(os.path.join(current, 'ns_employee.csv'))
