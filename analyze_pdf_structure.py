import fitz
import sys

def analyze_pdf(pdf_path):
    output = []
    output.append(f"Analyzing: {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
        output.append(f"Total Pages: {len(doc)}")
        
        for i, page in enumerate(doc):
            if i >= 3: 
                break
                
            output.append(f"\n--- Page {i+1} ---")
            
            # Check for text
            text_blocks = page.get_text("blocks")
            output.append(f"Text Blocks: {len(text_blocks)}")
            if len(text_blocks) > 0:
                # remove newlines for cleaner output
                sample = text_blocks[0][4][:50].replace('\n', ' ')
                output.append(f"Sample text: {sample}...")
            else:
                output.append("No text blocks found (might be an image scan).")

            # Check for images
            images = page.get_images()
            output.append(f"Images: {len(images)}")
            
        doc.close()
    except Exception as e:
        output.append(f"Error: {e}")
    
    with open("analysis_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    analyze_pdf(r"C:\Users\matti\Downloads\AI_Health_Implementation_North_Star.pdf")
