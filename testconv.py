line = input()
line = line.split(' ')
exit_code = line[1]
code = " ".join(line[2:])
print(f'self.assertCompileExitCode({code}, {exit_code})')
