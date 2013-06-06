import csv
import boto
from multiprocessing import Pool


def write_data(filename):
    """
    This will be called by __main__ for each process in our Pool.
    Error handling and logging of results elided.
    Don't write production code like this!
    """
    conn = boto.connect_dynamodb(aws_access_key_id=MY_ID,
                                 aws_secret_access_key=MY_SECRET)
    table = conn.get_table('my_table_name')

    with open(filename, 'rb') as f:
        reader = csv.reader(f)
        items = []
        for row in reader:
            dyn_row = table.new_item(hash_key='{}',format(row[0]),
                                     attrs = {'series': row[1],
                                              'episode': row[2],
                                              'timestamp': row[3],
                                              'moddt': row[4] })
            items.append(dyn_row)

        if len(items) > 25:
            batch_items = items[:25]
            batch_list = conn.new_batch_write_list()
            batch_list.add_batch(table, batch_items)
            response = conn.batch_write_item(batch_list)
            if not response['UnprocessedItems']:
                items = items[25:]
            else:
                unprocessed = [ ui['PutRequest']['Item']['user']
                                for ui in
                                response['UnprocessedItems']['my_table_name']]
            for item in batch_items:
                if item['user'] not in unprocessed:
                    items.remove(item)

if __name__ == '__main__':
    files = ['xaao','xabf','xabw',... ]
    pool = Pool(processes=len(files))
    pool.map(write_data, files)
