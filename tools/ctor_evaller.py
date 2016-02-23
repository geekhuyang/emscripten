'''
Tries to evaluate global constructors, applying their effects ahead of time.
'''

import os, sys, json
import shared

js_file = sys.argv[1]
mem_init_file = sys.argv[2]

temp_file = js_file + '.ctorEval.js'

# keep running whlie we succeed in removing a constructor

removed_one = False

while True:
  shared.logging.debug('ctor_evaller: trying to eval a global constructor')
  # pass the js and the mem init as extra info
  full = open(js_file).read() + '''\n// EXTRA_INFO:{"memInit":''' + json.dumps(map(ord, open(mem_init_file, 'rb').read())) + "}"
  open(temp_file, 'w').write(full)
  proc = Popen(shared.NODE_JS + [shared.path_from_root('tools', 'js-optimizer.js'), temp_file, 'evalCtor'], stdout=PIPE, stderr=PIPE)
  out, err = proc.communicate()
  if proc.returncode != 0:
    shared.logging.debug('ctor_evaller: done')
    break # that's it, no more luck. either no ctors, or we failed to eval a ctor
  # we succeeded. out contains the new JS, err contains the new memory init
  shared.logging.debug('ctor_evaller: success!')
  open(js_file, 'w').write(out)
  open(mem_init_file, 'wb').write(''.join(map(chr, json.loads(err))))
  removed_one = True

# If we removed one, dead function elimination can help us

if removed_one:
  shared.logging.debug('ctor_evaller: JSDFE')
  proc = Popen(shared.NODE_JS + [shared.path_from_root('tools', 'js-optimizer.js'), js_file, 'JSDFE'], stdout=PIPE)
  out, err = proc.communicate()
  assert proc.returncode == 0
  open(js_file, 'w').write(out)

