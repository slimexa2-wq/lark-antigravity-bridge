const fs = require('fs');
let content = fs.readFileSync('tests/unit/card/adaptive-throttler.test.ts', 'utf8');
const expected = "});";
let actualEnds = 0;
for(let i=content.length-1; i>=0; i--) {
  if (content[i] === '}' && content[i-1] === ')') {
     actualEnds++;
  }
}
fs.writeFileSync('tests/unit/card/adaptive-throttler.test.ts', content + "\n});\n");
