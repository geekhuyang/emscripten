'''
Tries to evaluate global constructors, applying their effects ahead of time.

This is an LTO-like operation, and to avoid parsing the entire tree, we operate on the text in python
'''

import os, sys, json
import shared, js_optimizer

js_file = sys.argv[1]
mem_init_file = sys.argv[2]
total_memory = int(sys.argv[3])

temp_file = js_file + '.ctorEval.js'

# helpers

def eval_ctor(js, mem_init):
  # Find the global ctors
  ctors_start = js.find('__ATINIT__.push(')
  if ctors_start < 0: return False
  ctors_end = js.find('});', ctors_start)
  if ctors_end < 0: return False
  ctors_end += 3
  ctors_text = js[ctors_start:ctors_end]
  ctors = filter(lambda ctor: ctor.endswith('()') and not ctor == 'function()', ctors_text.split(' '))
  if len(ctors) == 0: return False
  ctor = ctors[0]
  shared.logging.debug('trying to eval ctor: ' + ctor)
  # Find the asm module, and receive the mem init.
  asm = js[js.find(js_optimizer.start_asm_marker):js.find(js_optimizer.end_asm_marker)]
  assert len(asm) > 0
  asm = asm.replace('use asm', 'not asm') # don't try to validate this
  # Generate a safe sandboxed environment. We replace all ffis with errors. Otherwise,
  # asm.js can't call outside, so we are ok.
  open(temp_file, 'w').write('''
var buffer = new ArrayBuffer(%s);

// Instantiate asm
%s
(globalArg, libraryArg, buffer);

// Try to run the constructor
asm['%s']();

// We succeeded - verify asm global vars, and write out new mem init

''' % (total_memory, asm, ctor))
  # Execute the sandboxed code. If an error happened due to calling an ffi, that's fine,
  # us exiting with an error tells the caller that we failed.
  proc = Popen(shared.NODE_JS + [temp_file], stdout=PIPE)
  out, err = proc.communicate()
  if proc.returncode != 0: return False
  # Success! out contains the new mem init
  if len(ctors) == 1:
    new_ctors = ''
  else:
    new_ctors = ctors_text[:ctors_text.find('(') + 1] + ctors_text[ctors_text.find(',')+1:]
  js = js[:ctors_start] + new_ctors = js[ctors_end:]
  return out

# main

# keep running whlie we succeed in removing a constructor

removed_one = False

while True:
  shared.logging.debug('ctor_evaller: trying to eval a global constructor')
  js = open(js_file).read()
  mem_init json.dumps(map(ord, open(mem_init_file, 'rb').read()))
  if not eval_ctor(js, mem_init):
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

