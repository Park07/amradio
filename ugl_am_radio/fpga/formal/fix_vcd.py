import re, glob

for f in glob.glob('wd_cover/engine_0/trace*.vcd'):
    with open(f, 'r') as file:
        content = file.read()
    content = content.replace('$timescale 1ns $end', '$timescale 1s $end')
    content = re.sub(r'#(\d+)', lambda m: f'#{int(m.group(1))//10}', content)
    with open(f, 'w') as file:
        file.write(content)
    print(f'Fixed {f}')