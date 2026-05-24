const fs = require("fs");
const path = require("path");

const mdPath = path.join(__dirname, "Claude.md");
const md = fs.readFileSync(mdPath, "utf-8");

function parseAndCreateFiles(mdContent) {
  let created = 0;
  const lines = mdContent.split(/\r?\n/);
  
  console.log(`📄 Processing ${lines.length} lines from markdown file...`);
  
  for (let i = 0; i < lines.length; i++) {
    // Look for the pattern: ```filepath```language
    const fileLineMatch = lines[i].match(/^```###\s+([^`]+)```(\w+)/);
    
    if (fileLineMatch) {
      const filepath = fileLineMatch[1].trim();
      const language = fileLineMatch[2];
      
      console.log(`🔍 Found file: ${filepath} (${language})`);

      if (filepath.includes('*')) {
        console.warn(`⚠️ Skipping wildcard: ${filepath}`);
        continue;
      }

      let codeContent = [];
      let j = i + 1;
      
      // Collect content until we hit the next file header or end of file
      while (j < lines.length && !lines[j].match(/^```###\s+[^`]+```\w+/)) {
        codeContent.push(lines[j]);
        j++;
      }
      
      // Remove the last line if it's just ``` (closing backticks)
      const content = codeContent.join("\n").replace(/\n```$/, "").trim();
      
      if (content) {
        const fullPath = path.join(__dirname, filepath);
        
        try {
          fs.mkdirSync(path.dirname(fullPath), { recursive: true });
          fs.writeFileSync(fullPath, content, "utf-8");
          console.log(`✅ Created: ${filepath}`);
          created++;
        } catch (error) {
          console.error(`❌ Error creating ${filepath}:`, error.message);
        }
        
        i = j - 1; // Skip to the end of this section
      } else {
        console.warn(`⚠️ No content found for: ${filepath}`);
      }
    }
  }

  if (created === 0) {
    console.log("❌ No files created.");
  } else {
    console.log(`🎉 Successfully created ${created} files!`);
  }
}

parseAndCreateFiles(md);