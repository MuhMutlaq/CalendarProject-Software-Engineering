"""
OCR Date Detection System
Detects and highlights dates in various formats using EasyOCR and OpenCV
Supports PDF, PNG, and JPG files
"""

import cv2
import numpy as np
import easyocr
import re
from pathlib import Path
import argparse
from typing import List, Tuple, Dict, Optional
import pdf2image
from PIL import Image
import os
import sys


class DateOCRDetector:
    """OCR system for detecting and highlighting dates in documents"""
    
    def __init__(self, languages: List[str] = ['en'], gpu: bool = True):
        """
        Initialize the Date OCR Detector
        
        Args:
            languages: List of language codes for EasyOCR
            gpu: Whether to use GPU acceleration
        """
        self.reader = easyocr.Reader(languages, gpu=gpu)
        
        # Date regex patterns - handles various formats
        self.date_patterns = [
            # MM/DD/YYYY, DD/MM/YYYY, MM/DD/YY, DD/MM/YY
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            
            # MM-DD-YYYY, DD-MM-YYYY, MM-DD-YY, DD-MM-YY
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',
            
            # YYYY/MM/DD, YYYY-MM-DD
            r'\b\d{4}/\d{1,2}/\d{1,2}\b',
            r'\b\d{4}-\d{1,2}-\d{1,2}\b',
            
            # Month DD, YYYY or DD Month YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}\b',
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4}\b',
            
            # Full month names
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}\b',
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4}\b',
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.date_patterns]
    
    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[np.ndarray]:
        """
        Convert PDF pages to images
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for conversion
            
        Returns:
            List of images as numpy arrays
        """
        try:
            # Convert PDF to PIL Images
            pil_images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
            
            # Convert PIL Images to numpy arrays
            images = []
            for pil_image in pil_images:
                # Convert PIL Image to numpy array
                image_array = np.array(pil_image)
                # Convert RGB to BGR for OpenCV
                if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                    image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
                images.append(image_array)
            
            return images
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []
    
    def load_image(self, file_path: str) -> Optional[np.ndarray]:
        """
        Load an image from file
        
        Args:
            file_path: Path to image file
            
        Returns:
            Image as numpy array or None if failed
        """
        try:
            # Check file extension
            extension = Path(file_path).suffix.lower()
            
            if extension == '.pdf':
                # For PDF, return the first page for now
                images = self.pdf_to_images(file_path)
                return images[0] if images else None
            elif extension in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']:
                # Load image using OpenCV
                image = cv2.imread(file_path)
                return image
            else:
                print(f"Unsupported file format: {extension}")
                return None
        except Exception as e:
            print(f"Error loading image: {e}")
            return None
    
    def detect_text(self, image: np.ndarray) -> List[Tuple]:
        """
        Detect text in image using EasyOCR
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of text detections (bbox, text, confidence)
        """
        try:
            # Run EasyOCR
            results = self.reader.readtext(image)
            return results
        except Exception as e:
            print(f"Error detecting text: {e}")
            return []
    
    def is_date(self, text: str) -> bool:
        """
        Check if text contains a date pattern
        
        Args:
            text: Text to check
            
        Returns:
            True if text matches date pattern
        """
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True
        return False
    
    def find_date_regions(self, ocr_results: List[Tuple]) -> List[Dict]:
        """
        Find text regions containing dates
        
        Args:
            ocr_results: Results from EasyOCR
            
        Returns:
            List of date regions with bounding boxes and text
        """
        date_regions = []
        
        for bbox, text, confidence in ocr_results:
            # Check if text contains a date
            if self.is_date(text):
                # Extract bounding box coordinates
                points = np.array(bbox, dtype=np.int32)
                x_min = min(points[:, 0])
                y_min = min(points[:, 1])
                x_max = max(points[:, 0])
                y_max = max(points[:, 1])
                
                date_regions.append({
                    'bbox': (x_min, y_min, x_max, y_max),
                    'points': points,
                    'text': text,
                    'confidence': confidence
                })
        
        return date_regions
    
    def draw_date_boxes(self, image: np.ndarray, date_regions: List[Dict], 
                       box_color: Tuple[int, int, int] = (0, 255, 0),
                       text_color: Tuple[int, int, int] = (0, 0, 255),
                       thickness: int = 2) -> np.ndarray:
        """
        Draw bounding boxes around detected dates
        
        Args:
            image: Input image
            date_regions: List of date regions to highlight
            box_color: Color for bounding boxes (BGR)
            text_color: Color for text labels (BGR)
            thickness: Line thickness
            
        Returns:
            Image with drawn boxes
        """
        # Create a copy to avoid modifying original
        result_image = image.copy()
        
        for region in date_regions:
            x_min, y_min, x_max, y_max = region['bbox']
            
            # Draw rectangle around date
            cv2.rectangle(result_image, (x_min, y_min), (x_max, y_max), 
                         box_color, thickness)
            
            # Add "Date" label above the box
            label = "Date"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 2
            
            # Get text size for background
            (text_width, text_height), baseline = cv2.getTextSize(
                label, font, font_scale, font_thickness
            )
            
            # Draw background rectangle for label
            label_y = y_min - 5 if y_min > 30 else y_max + text_height + 5
            cv2.rectangle(result_image, 
                         (x_min, label_y - text_height - 5),
                         (x_min + text_width + 10, label_y + 5),
                         box_color, -1)
            
            # Draw label text
            cv2.putText(result_image, label,
                       (x_min + 5, label_y),
                       font, font_scale, (255, 255, 255), font_thickness)
            
            # Optionally add the detected text below
            detected_text = f"{region['text'][:30]}..." if len(region['text']) > 30 else region['text']
            cv2.putText(result_image, detected_text,
                       (x_min, y_max + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
        
        return result_image
    
    def process_file(self, file_path: str, output_dir: str = None, 
                    show_result: bool = False) -> Dict:
        """
        Process a single file to detect and highlight dates
        
        Args:
            file_path: Path to input file
            output_dir: Directory to save results
            show_result: Whether to display result
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'file': file_path,
            'status': 'failed',
            'dates_found': [],
            'output_files': []
        }
        
        print(f"\nProcessing: {file_path}")
        
        # Check if file is PDF
        if Path(file_path).suffix.lower() == '.pdf':
            images = self.pdf_to_images(file_path)
            if not images:
                print("Failed to convert PDF")
                return results
        else:
            image = self.load_image(file_path)
            if image is None:
                print("Failed to load image")
                return results
            images = [image]
        
        # Process each image/page
        all_dates = []
        for page_num, image in enumerate(images, 1):
            print(f"Processing page {page_num}/{len(images)}...")
            
            # Detect text
            ocr_results = self.detect_text(image)
            print(f"Found {len(ocr_results)} text regions")
            
            # Find date regions
            date_regions = self.find_date_regions(ocr_results)
            print(f"Found {len(date_regions)} date regions")
            
            # Store dates
            for region in date_regions:
                all_dates.append({
                    'page': page_num,
                    'text': region['text'],
                    'confidence': region['confidence']
                })
            
            # Draw boxes
            result_image = self.draw_date_boxes(image, date_regions)
            
            # Save output
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                base_name = Path(file_path).stem
                if len(images) > 1:
                    output_path = os.path.join(output_dir, f"{base_name}_page{page_num}_dates.png")
                else:
                    output_path = os.path.join(output_dir, f"{base_name}_dates.png")
                
                cv2.imwrite(output_path, result_image)
                results['output_files'].append(output_path)
                print(f"Saved result to: {output_path}")
            
            # Show result if requested
            if show_result:
                # Resize for display if too large
                height, width = result_image.shape[:2]
                if width > 1200:
                    scale = 1200 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    display_image = cv2.resize(result_image, (new_width, new_height))
                else:
                    display_image = result_image
                
                cv2.imshow(f'Detected Dates - Page {page_num}', display_image)
                cv2.waitKey(0)
        
        # Update results
        results['status'] = 'success'
        results['dates_found'] = all_dates
        
        # Close windows if opened
        if show_result:
            cv2.destroyAllWindows()
        
        return results
    
    def process_directory(self, directory: str, output_dir: str = None,
                         extensions: List[str] = None) -> List[Dict]:
        """
        Process all supported files in a directory
        
        Args:
            directory: Input directory path
            output_dir: Output directory for results
            extensions: File extensions to process
            
        Returns:
            List of processing results
        """
        if extensions is None:
            extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif']
        
        all_results = []
        
        # Find all files with supported extensions
        for ext in extensions:
            for file_path in Path(directory).glob(f'*{ext}'):
                result = self.process_file(str(file_path), output_dir)
                all_results.append(result)
        
        return all_results

def main():
    """Main function to run the Date OCR Detector"""
    parser = argparse.ArgumentParser(description='OCR Date Detection System')
    parser.add_argument('input', help='Input file or directory path')
    parser.add_argument('-o', '--output', default='./backend/output_dates', 
                       help='Output directory for results (default: output_dates)')
    parser.add_argument('-s', '--show', action='store_true',
                       help='Show detection results')
    parser.add_argument('--gpu', action='store_true',
                       help='Use GPU for OCR (if available)')
    parser.add_argument('-l', '--languages', nargs='+', default=['en'],
                       help='Languages for OCR (default: en)')
    
    args = parser.parse_args()
    
    # Create detector
    print(f"Initializing Date OCR Detector...")
    print(f"Languages: {args.languages}")
    print(f"GPU: {args.gpu}")
    
    detector = DateOCRDetector(languages=args.languages, gpu=args.gpu)
    
    # Process input
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Process single file
        results = detector.process_file(str(input_path), args.output, args.show)
        
        # Print summary
        print("\n" + "="*50)
        print("DETECTION SUMMARY")
        print("="*50)
        print(f"File: {results['file']}")
        print(f"Status: {results['status']}")
        print(f"Total dates found: {len(results['dates_found'])}")
        
        if results['dates_found']:
            print("\nDetected dates:")
            for date_info in results['dates_found']:
                print(f"  Page {date_info['page']}: {date_info['text']} "
                     f"(confidence: {date_info['confidence']:.2f})")
        
        if results['output_files']:
            print(f"\nOutput saved to:")
            for output_file in results['output_files']:
                print(f"  {output_file}")
    
    elif input_path.is_dir():
        # Process directory
        results = detector.process_directory(str(input_path), args.output)
        
        # Print summary
        print("\n" + "="*50)
        print("BATCH PROCESSING SUMMARY")
        print("="*50)
        print(f"Total files processed: {len(results)}")
        
        successful = sum(1 for r in results if r['status'] == 'success')
        total_dates = sum(len(r['dates_found']) for r in results)
        
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")
        print(f"Total dates found: {total_dates}")
        
        # Detailed results
        print("\nDetailed results:")
        for result in results:
            print(f"\n  {Path(result['file']).name}:")
            print(f"    Status: {result['status']}")
            print(f"    Dates found: {len(result['dates_found'])}")
            if result['dates_found']:
                for date_info in result['dates_found'][:3]:  # Show first 3
                    print(f"      - {date_info['text']}")
                if len(result['dates_found']) > 3:
                    print(f"      ... and {len(result['dates_found']) - 3} more")
    else:
        print(f"Error: {input_path} is neither a file nor a directory")
        return 1
    
    print("\nProcessing complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())