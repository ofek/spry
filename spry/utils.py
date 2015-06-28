



def get_chunk_data(length, num_parts):
    chunk_size = length // num_parts
    chunk_data = []

    start = 0
    for i in range(num_parts):
        end = start + chunk_size
        if i == num_parts - 1:
            end += length - end
        chunk_data.append({'start': start, 'end': end - 1,
                           'length': end - start})
        start = end

    return chunk_data

def create_null_file(path, size=1):
    if size < 1:
        raise ValueError('size must be an integer >= 1')

    with open(path, 'wb') as f:
        f.seek(size - 1)
        f.write(b'\x00')
