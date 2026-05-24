const fs = require("fs");
const path = require("path");

const mdPath = path.join(__dirname, "llamaAT1.md");
const md = fs.readFileSync(mdPath, "utf-8");

function parseAndCreateFiles(mdContent) {
  let created = 0;
  const lines = mdContent.split(/\r?\n/);
  
  for (let i = 0; i < lines.length; i++) {
    // Regex to find a line starting with one or more '#' followed by a space and a backticked filename
    const fileLineMatch = lines[i].match(/^#+.*`([^`]+)`/);
    
    if (fileLineMatch) {
      const filename = fileLineMatch[1].trim();

      // Skip invalid filenames containing the * wildcard
      if (filename.includes('*')) {
        console.warn(`⚠️ Skipping file with invalid filename: "${filename}". This is likely a placeholder for multiple files.`);
        continue;
      }

      let codeBlockStart = -1;

      // Scan for the start of the code block (```) on subsequent lines
      for (let j = i + 1; j < lines.length; j++) {
        if (lines[j].trim().startsWith("```")) {
          codeBlockStart = j;
          break;
        }
      }

      if (codeBlockStart !== -1) {
        let codeBlockEnd = -1;
        // Find the end of the code block (```)
        for (let k = codeBlockStart + 1; k < lines.length; k++) {
          if (lines[k].trim().startsWith("```")) {
            codeBlockEnd = k;
            break;
          }
        }
        
        if (codeBlockEnd !== -1) {
          const content = lines.slice(codeBlockStart + 1, codeBlockEnd).join("\n");
          const fullPath = path.join(__dirname, filename);
          
          fs.mkdirSync(path.dirname(fullPath), { recursive: true });
          fs.writeFileSync(fullPath, content, "utf-8");
          console.log(`✅ Created: ${filename}`);
          created++;
          
          i = codeBlockEnd; // Continue scanning from after the current code block
        } else {
          console.warn(`⚠️ Found filename (${filename}) but no closing code block.`);
        }
      } else {
        console.warn(`⚠️ Found filename (${filename}) but no code block found after it.`);
      }
    }
  }

  if (created === 0) {
    console.warn("⚠️ No valid code blocks with filenames found. Check markdown format.");
  }
}

parseAndCreateFiles(md);