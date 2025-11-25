import os
from typing import Tuple, List
from pathlib import Path

import logging
logging.basicConfig(level= logging.INFO)
logger= logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE= True
except ImportError:
    CV2_AVAILABLE= False
    logger.warning("OpenCV not available. Image preprocessing will be limited.")

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE= True
except ImportError:
    PIL_AVAILABLE= False
    logger.warning("Pillow not available. Image preprocessing will be limited.")


class ImagePreprocessor:
    """
    Preprocesses images for optimal OCR performance.
    Applies multiple enhancement techniques to improve text clarity.
    """

    def __init__(self, output_dir: str= "processed"):
        self.output_dir= output_dir
        os.makedirs(output_dir, exist_ok= True)

    def preprocess(self, image_path: str, enhance_level: str= "auto") -> str:
        """
        Main preprocessing pipeline. Applies optimal enhancements based on image analysis.
        
        Args:
            image_path: Path to input image
            enhance_level: "light", "medium", "heavy", or "auto"
            
        Returns:
            Path to preprocessed image
        """
        
        if not CV2_AVAILABLE and not PIL_AVAILABLE:
            logger.warning("No image processing library available, returning original")
            return image_path

        logger.info(f"Preprocessing image: {image_path}")
        
        # Read image
        if CV2_AVAILABLE:
            return self._preprocess_opencv(image_path, enhance_level)
        else:
            return self._preprocess_pil(image_path)

    def _preprocess_opencv(self, image_path: str, enhance_level: str) -> str:
        """OpenCV-based preprocessing pipeline for maximum quality."""
        
        # Read image
        img= cv2.imread(image_path)
        if img is None:
            logger.error(f"Failed to read image: {image_path}")
            return image_path

        original_height, original_width= img.shape[:2]
        logger.info(f"Original image size: {original_width}x{original_height}")

        # Step 1: Upscale if image is small (improves OCR accuracy)
        img= self._upscale_if_needed(img)

        # Step 2: Convert to grayscale
        gray= cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Step 3: Analyze image to determine best preprocessing
        if enhance_level == "auto":
            enhance_level= self._analyze_image(gray)
            logger.info(f"Auto-detected enhancement level: {enhance_level}")

        # Step 4: Apply denoising
        denoised= cv2.fastNlMeansDenoising(gray, None, h= 10, templateWindowSize= 7, searchWindowSize= 21)

        # Step 5: Apply adaptive thresholding or binarization based on level
        if enhance_level == "heavy":
            # Strong binarization for poor quality images
            processed= cv2.adaptiveThreshold(
                denoised, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize= 11,
                C= 2
            )
        elif enhance_level == "medium":
            # Moderate enhancement
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe= cv2.createCLAHE(clipLimit= 2.0, tileGridSize= (8, 8))
            processed= clahe.apply(denoised)
            # Light sharpening
            kernel= np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            processed= cv2.filter2D(processed, -1, kernel)
        else: # light
            # Light enhancement - preserve original quality
            clahe= cv2.createCLAHE(clipLimit= 1.5, tileGridSize= (8, 8))
            processed= clahe.apply(denoised)

        # Step 6: Deskew if needed
        processed= self._deskew(processed)

        # Step 7: Remove borders/noise at edges
        processed= self._remove_borders(processed)

        # Save processed image
        output_filename= f"processed_{Path(image_path).stem}.png"
        output_path= os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_path, processed)

        logger.info(f"Preprocessed image saved to: {output_path}")
        return output_path

    def _upscale_if_needed(self, image: np.ndarray, min_dimension: int= 1500) -> np.ndarray:
        """Upscale image if it's too small for good OCR."""
        
        height, width= image.shape[:2]
        
        if width < min_dimension or height < min_dimension:
            scale= max(min_dimension / width, min_dimension / height)
            scale= min(scale, 3.0) # Don't upscale more than 3x
            
            new_width= int(width * scale)
            new_height= int(height * scale)
            
            image= cv2.resize(image, (new_width, new_height), interpolation= cv2.INTER_CUBIC)
            logger.info(f"Upscaled image to: {new_width}x{new_height}")
        
        return image

    def _analyze_image(self, gray_img: np.ndarray) -> str:
        """Analyze image quality to determine optimal preprocessing level."""
        
        # Calculate image statistics
        mean_brightness= np.mean(gray_img)
        std_brightness= np.std(gray_img)
        
        # Calculate contrast using Laplacian variance
        laplacian_var= cv2.Laplacian(gray_img, cv2.CV_64F).var()
        
        logger.info(f"Image analysis - Mean: {mean_brightness:.1f}, Std: {std_brightness:.1f}, Sharpness: {laplacian_var:.1f}")

        # Determine enhancement level based on analysis
        if laplacian_var < 100:
            # Very blurry image
            return "heavy"
        elif laplacian_var < 500 or std_brightness < 40:
            # Moderately blurry or low contrast
            return "medium"
        else:
            # Good quality image
            return "light"

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Correct image rotation/skew for better OCR."""
        
        try:
            # Find all non-zero points
            coords= np.column_stack(np.where(image > 0))
            
            if len(coords) < 100:
                return image
            
            # Get rotation angle
            angle= cv2.minAreaRect(coords)[-1]
            
            if angle < -45:
                angle= 90 + angle
            elif angle > 45:
                angle= angle - 90
            
            # Only correct if skew is significant but not too extreme
            if abs(angle) > 0.5 and abs(angle) < 15:
                (h, w)= image.shape[:2]
                center= (w // 2, h // 2)
                M= cv2.getRotationMatrix2D(center, angle, 1.0)
                image= cv2.warpAffine(
                    image, M, (w, h),
                    flags= cv2.INTER_CUBIC,
                    borderMode= cv2.BORDER_REPLICATE
                )
                logger.info(f"Deskewed image by {angle:.2f} degrees")
        except Exception as e:
            logger.warning(f"Deskew failed: {e}")
        
        return image

    def _remove_borders(self, image: np.ndarray) -> np.ndarray:
        """Remove black borders and noise at image edges."""
        
        try:
            # Find contours
            contours, _= cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Get bounding box of all content
                all_contours= np.vstack(contours)
                x, y, w, h= cv2.boundingRect(all_contours)
                
                # Add small padding
                padding= 10
                x= max(0, x - padding)
                y= max(0, y - padding)
                w= min(image.shape[1] - x, w + 2 * padding)
                h= min(image.shape[0] - y, h + 2 * padding)
                
                # Crop if significant border detected
                if w > image.shape[1] * 0.8 and h > image.shape[0] * 0.8:
                    image= image[y: (y + h), x: (x + w)]
        except Exception as e:
            logger.warning(f"Border removal failed: {e}")
        
        return image

    def _preprocess_pil(self, image_path: str) -> str:
        """PIL-based preprocessing (fallback when OpenCV not available)."""
        
        image= Image.open(image_path)
        
        # Convert to grayscale
        if image.mode != 'L':
            image= image.convert('L')
        
        # Enhance contrast
        enhancer= ImageEnhance.Contrast(image)
        image= enhancer.enhance(1.5)
        
        # Enhance sharpness
        enhancer= ImageEnhance.Sharpness(image)
        image= enhancer.enhance(2.0)
        
        # Apply edge enhancement
        image= image.filter(ImageFilter.EDGE_ENHANCE)
        
        # Save
        output_filename= f"processed_{Path(image_path).stem}.png"
        output_path= os.path.join(self.output_dir, output_filename)
        image.save(output_path)
        
        logger.info(f"PIL preprocessed image saved to: {output_path}")
        return output_path

    def thicken_text(self, image_path: str, kernel_size: int= 3) -> str:
        """
        Make text/fonts thicker using morphological dilation.
        Useful for thin or faint text that's hard to read.
        
        Args:
            image_path: Path to input image
            kernel_size: Size of dilation kernel (2-4 recommended, higher = thicker)
            
        Returns:
            Path to processed image with thicker text
        """
        
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available for text thickening")
            return image_path
        
        image= cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return image_path
        
        # Invert image (text becomes white on black for dilation)
        inverted= cv2.bitwise_not(image)
        
        # Create dilation kernel
        kernel= np.ones((kernel_size, kernel_size), np.uint8)
        
        # Apply dilation (makes white areas larger = thicker text when inverted back)
        dilated= cv2.dilate(inverted, kernel, iterations= 1)
        
        # Invert back
        result= cv2.bitwise_not(dilated)
        
        # Save
        output_filename= f"thick_{Path(image_path).stem}.png"
        output_path= os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_path, result)
        
        logger.info(f"Thickened text (kernel= {kernel_size}) saved to: {output_path}")
        return output_path

    def thin_text(self, image_path: str, kernel_size: int= 2) -> str:
        """
        Make text/fonts thinner using morphological erosion.
        Useful for bold or thick text that's bleeding together.
        
        Args:
            image_path: Path to input image
            kernel_size: Size of erosion kernel (1-3 recommended, higher = thinner)
            
        Returns:
            Path to processed image with thinner text
        """
        
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available for text thinning")
            return image_path
        
        image= cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return image_path
        
        # Invert image
        inverted= cv2.bitwise_not(image)
        
        # Create erosion kernel
        kernel= np.ones((kernel_size, kernel_size), np.uint8)
        
        # Apply erosion (makes white areas smaller = thinner text when inverted back)
        eroded= cv2.erode(inverted, kernel, iterations= 1)
        
        # Invert back
        result= cv2.bitwise_not(eroded)
        
        # Save
        output_filename= f"thin_{Path(image_path).stem}.png"
        output_path= os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_path, result)
        
        logger.info(f"Thinned text saved to: {output_path}")
        return output_path

    def enhance_table_structure(self, image_path: str) -> str:
        """
        Enhance table lines and structure for better cell detection.
        Makes horizontal and vertical lines more prominent.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to enhanced image
        """
        
        if not CV2_AVAILABLE:
            return image_path
        
        image= cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return image_path
        
        # Threshold to binary
        _, binary= cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Detect horizontal lines
        horizontal_kernel= cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines= cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations= 2)
        
        # Detect vertical lines
        vertical_kernel= cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines= cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations= 2)
        
        # Combine lines
        table_structure= cv2.add(horizontal_lines, vertical_lines)
        
        # Dilate lines to make them more prominent
        kernel= np.ones((2, 2), np.uint8)
        table_structure= cv2.dilate(table_structure, kernel, iterations= 1)
        
        # Combine with original (enhanced lines)
        result= cv2.bitwise_not(binary)
        result= cv2.subtract(result, table_structure)
        
        # Save
        output_filename= f"table_enhanced_{Path(image_path).stem}.png"
        output_path= os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_path, cv2.bitwise_not(result))
        
        logger.info(f"Table structure enhanced: {output_path}")
        return output_path

    def preprocess_for_table(self, image_path: str) -> str:
        """
        Specialized preprocessing for table/schedule images.
        Optimized for documents with grid structures.
        Applies text thickening for better OCR of table content.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to preprocessed image
        """
        
        if not CV2_AVAILABLE:
            return self.preprocess(image_path)

        image= cv2.imread(image_path)
        if image is None:
            return image_path

        # Upscale for better detail
        image= self._upscale_if_needed(image, min_dimension= 2000)

        # Convert to grayscale
        gray= cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Denoise while preserving edges (important for table lines)
        denoised= cv2.bilateralFilter(gray, 9, 75, 75)

        # Apply CLAHE for contrast
        clahe= cv2.createCLAHE(clipLimit= 2.0, tileGridSize= (8, 8))
        enhanced= clahe.apply(denoised)

        # Sharpen to make text clearer
        kernel= np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpened= cv2.filter2D(enhanced, -1, kernel)

        # Apply adaptive thresholding for clean binary image
        binary= cv2.adaptiveThreshold(
            sharpened, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize= 15,
            C= 4
        )
        
        # Thicken text slightly for better OCR (dilation on inverted)
        inverted= cv2.bitwise_not(binary)
        kernel_dilate= np.ones((2, 2), np.uint8)
        dilated= cv2.dilate(inverted, kernel_dilate, iterations= 1)
        thickened= cv2.bitwise_not(dilated)

        # Deskew
        thickened= self._deskew(thickened)

        # Save
        output_filename= f"table_processed_{Path(image_path).stem}.png"
        output_path= os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_path, thickened)

        logger.info(f"Table-optimized image saved to: {output_path}")
        return output_path

    def preprocess_for_ocr_accuracy(self, image_path: str, text_thickness: str= "auto") -> str:
        """
        Advanced preprocessing specifically optimized for maximum OCR accuracy.
        Analyzes text and applies appropriate thickness adjustment.
        
        Args:
            image_path: Path to input image
            text_thickness: "thin", "normal", "thick", or "auto"
            
        Returns:
            Path to preprocessed image
        """
        
        if not CV2_AVAILABLE:
            return self.preprocess(image_path)

        image= cv2.imread(image_path)
        if image is None:
            return image_path

        # Step 1: Upscale significantly for better detail
        image= self._upscale_if_needed(image, min_dimension= 2500)
        
        # Step 2: Convert to grayscale
        gray= cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Step 3: Analyze text thickness if auto
        if text_thickness == "auto":
            text_thickness= self._analyze_text_thickness(gray)
            logger.info(f"Auto-detected text thickness: {text_thickness}")
        
        # Step 4: Strong denoising
        denoised= cv2.fastNlMeansDenoising(gray, None, h= 12, templateWindowSize= 7, searchWindowSize= 21)
        
        # Step 5: High contrast CLAHE
        clahe= cv2.createCLAHE(clipLimit= 3.0, tileGridSize= (8, 8))
        enhanced= clahe.apply(denoised)
        
        # Step 6: Adaptive binarization
        binary= cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize= 11,
            C= 2
        )
        
        # Step 7: Apply text thickness adjustment
        if text_thickness == "thick":
            # Thicken text using dilation (makes text bolder/more visible)
            inverted= cv2.bitwise_not(binary)
            # Use 3x3 kernel for noticeable thickening
            kernel= np.ones((3, 3), np.uint8)
            processed= cv2.dilate(inverted, kernel, iterations= 1)
            binary= cv2.bitwise_not(processed)
            logger.info("Applied text thickening (3x3 kernel)")
        elif text_thickness == "thin":
            # Thin text using erosion (reduces bold/bleeding text)
            inverted= cv2.bitwise_not(binary)
            kernel= np.ones((2, 2), np.uint8)
            processed= cv2.erode(inverted, kernel, iterations= 1)
            binary= cv2.bitwise_not(processed)
            logger.info("Applied text thinning (2x2 kernel)")
        # else "normal" - no adjustment
        
        # Step 8: Final sharpening
        kernel_sharp= np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened= cv2.filter2D(binary, -1, kernel_sharp)
        
        # Step 9: Deskew
        final= self._deskew(sharpened)
        
        # Save
        output_filename= f"ocr_optimized_{Path(image_path).stem}.png"
        output_path= os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_path, final)
        
        logger.info(f"OCR-optimized image saved to: {output_path}")
        return output_path

    def _analyze_text_thickness(self, gray_img: np.ndarray) -> str:
        """
        Analyze image to determine if text needs to be thickened or thinned.
        
        Returns: "thin", "normal", or "thick" recommendation
        """
        
        # Binarize
        _, binary= cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Calculate ratio of black pixels (text) to total
        text_ratio= np.sum(binary > 0) / binary.size
        
        # Calculate average stroke width using distance transform
        dist= cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        avg_stroke_width= np.mean(dist[dist > 0]) if np.any(dist > 0) else 0
        
        logger.info(f"Text analysis - Ratio: {text_ratio:.4f}, Avg stroke width: {avg_stroke_width:.2f}")
        
        # Determine recommendation
        if avg_stroke_width < 1.5 or text_ratio < 0.05:
            # Thin/faint text - needs thickening
            return "thick"
        elif avg_stroke_width > 4.0 or text_ratio > 0.25:
            # Bold/heavy text - needs thinning
            return "thin"
        else:
            # Normal text
            return "normal"

    def preprocess_minimal(self, image_path: str) -> str:
        """
        Minimal preprocessing - just upscale and light contrast enhancement.
        Preserves original image structure without heavy modifications.
        Best for high-quality PDFs where table structure needs to be preserved.
        
        Args:
            image_path: Path to input image
            
        Returns:
            Path to preprocessed image
        """
        
        if not CV2_AVAILABLE:
            return image_path

        img= cv2.imread(image_path)
        if img is None:
            return image_path

        # Step 1: Upscale for better detail
        img= self._upscale_if_needed(img, min_dimension= 2000)
        
        # Step 2: Convert to grayscale
        gray= cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Step 3: Light CLAHE only - no binarization
        clahe= cv2.createCLAHE(clipLimit= 1.5, tileGridSize= (8, 8))
        enhanced= clahe.apply(gray)
        
        # Step 4: Very light sharpening
        kernel= np.array([[0, -0.5, 0], [-0.5, 3, -0.5], [0, -0.5, 0]])
        sharpened= cv2.filter2D(enhanced, -1, kernel)
        
        # Save
        output_filename= f"minimal_{Path(image_path).stem}.png"
        output_path= os.path.join(self.output_dir, output_filename)
        cv2.imwrite(output_path, sharpened)
        
        logger.info(f"Minimal preprocessed image saved to: {output_path}")
        return output_path


class PDFImageExtractor:
    """
    Extracts images from PDFs for OCR processing.
    Handles both text-based and image-based PDFs.
    """

    def __init__(self, output_dir: str = "pdf_pages"):
        self.output_dir= output_dir
        os.makedirs(output_dir, exist_ok= True)

    def extract_pages_as_images(
        self, 
        pdf_path: str, 
        dpi: int = 200
    ) -> List[str]:
        """
        Convert PDF pages to images for OCR processing.
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for conversion (higher = better quality but slower)
            
        Returns:
            List of paths to extracted page images
        """
        logger.info(f"Extracting pages from PDF: {pdf_path}")
        image_paths= []

        try:
            # Try pdf2image first (best quality)
            from pdf2image import convert_from_path
            
            images= convert_from_path(
                pdf_path, 
                dpi= dpi,
                fmt= "png",
                thread_count= 2
            )
            
            for i, image in enumerate(images):
                output_path= os.path.join(self.output_dir, f"{Path(pdf_path).stem}_page_{i + 1}.png")
                image.save(output_path, "PNG")
                image_paths.append(output_path)
                logger.info(f"Extracted page {i + 1}: {output_path}")

        except ImportError:
            logger.warning("pdf2image not available, trying alternative methods")
            
            try:
                # Try PyMuPDF as alternative
                import fitz  # PyMuPDF
                
                doc= fitz.open(pdf_path)
                for i, page in enumerate(doc):
                    # Render page to image
                    mat= fitz.Matrix(dpi / 72, dpi / 72)
                    pix= page.get_pixmap(matrix= mat)
                    
                    output_path= os.path.join(self.output_dir, f"{Path(pdf_path).stem}_page_{i + 1}.png")
                    pix.save(output_path)
                    image_paths.append(output_path)
                    logger.info(f"Extracted page {i + 1}: {output_path}")
                
                doc.close()
                
            except ImportError:
                logger.error("No PDF to image converter available. Install pdf2image or PyMuPDF.")
                raise ImportError(
                    "PDF image extraction requires pdf2image or PyMuPDF. "
                    "Install with: pip install pdf2image poppler-utils OR pip install PyMuPDF"
                )

        return image_paths


def preprocess_for_extraction(
    file_path: str, 
    is_pdf: bool = False
) -> Tuple[str, List[str]]:
    """
    Main function to preprocess a file for OCR extraction.
    
    Args:
        file_path: Path to image or PDF file
        is_pdf: Whether the file is a PDF
        
    Returns:
        Tuple of (preprocessed_path, list_of_page_paths)
    """
    preprocessor= ImagePreprocessor(output_dir= "processed_images")
    
    if is_pdf:
        # Extract PDF pages as images
        pdf_extractor= PDFImageExtractor(output_dir= "pdf_pages")
        page_images= pdf_extractor.extract_pages_as_images(file_path)
        
        # Preprocess each page
        processed_pages= []
        for page_path in page_images:
            processed= preprocessor.preprocess_for_table(page_path)
            processed_pages.append(processed)
        
        return processed_pages[0] if processed_pages else file_path, processed_pages
    else:
        # Single image
        processed= preprocessor.preprocess_for_table(file_path)
        return processed, [processed]