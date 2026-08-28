package main

import (
	"image"
	"image/color"
	"math"
)

func drawIcon(size int, printing bool, progress float64, offline bool) *image.RGBA {
	img := image.NewRGBA(image.Rect(0, 0, size, size))
	cx, cy := float64(size)/2-0.5, float64(size)/2-0.5
	outer := float64(size)/2 - 1.0
	inner := outer - float64(size)*0.18
	if inner < 4 {
		inner = 4
	}
	for y := 0; y < size; y++ {
		for x := 0; x < size; x++ {
			img.SetRGBA(x, y, color.RGBA{0, 0, 0, 0})
		}
	}

	switch {
	case offline:
		fillCircle(img, cx, cy, outer, color.RGBA{72, 76, 82, 255})
		ring(img, cx, cy, inner, outer, 0, 1, color.RGBA{120, 124, 130, 255})
		drawPrinter(img, size, color.RGBA{210, 214, 218, 255})
	case !printing:
		fillCircle(img, cx, cy, outer, color.RGBA{22, 163, 74, 255})
		ring(img, cx, cy, inner, outer, 0, 1, color.RGBA{187, 247, 208, 255})
		drawPrinter(img, size, color.RGBA{240, 253, 244, 255})
	default:
		fillCircle(img, cx, cy, inner-0.6, color.RGBA{17, 24, 28, 255})
		ring(img, cx, cy, inner, outer, 0, 1, color.RGBA{45, 55, 62, 255})
		p := progress / 100
		if p < 0 {
			p = 0
		}
		if p > 1 {
			p = 1
		}
		if p < 0.02 && progress > 0 {
			p = 0.02
		}
		ring(img, cx, cy, inner, outer, 0, p, color.RGBA{45, 212, 191, 255})
		drawPrinter(img, size, color.RGBA{226, 252, 247, 255})
	}
	return img
}

func fillCircle(img *image.RGBA, cx, cy, r float64, col color.RGBA) {
	b := img.Bounds()
	r2 := r * r
	for y := b.Min.Y; y < b.Max.Y; y++ {
		for x := b.Min.X; x < b.Max.X; x++ {
			dx := float64(x) - cx
			dy := float64(y) - cy
			if dx*dx+dy*dy <= r2 {
				img.SetRGBA(x, y, col)
			}
		}
	}
}

func ring(img *image.RGBA, cx, cy, r0, r1, from, to float64, col color.RGBA) {
	b := img.Bounds()
	for y := b.Min.Y; y < b.Max.Y; y++ {
		for x := b.Min.X; x < b.Max.X; x++ {
			dx := float64(x) - cx
			dy := float64(y) - cy
			d := math.Hypot(dx, dy)
			if d < r0 || d > r1 {
				continue
			}
			ang := math.Atan2(dx, -dy)
			if ang < 0 {
				ang += 2 * math.Pi
			}
			frac := ang / (2 * math.Pi)
			if frac+1e-6 >= from && frac <= to {
				img.SetRGBA(x, y, col)
			}
		}
	}
}

func drawPrinter(img *image.RGBA, size int, ink color.RGBA) {
	// Simple gantry + nozzle + bed, scaled to icon size.
	s := float64(size)
	cx := s / 2
	cy := s / 2
	dot := func(x, y float64) {
		ix, iy := int(math.Round(x)), int(math.Round(y))
		if ix >= 0 && iy >= 0 && ix < size && iy < size {
			img.SetRGBA(ix, iy, ink)
		}
	}
	hline := func(x0, x1, y float64) {
		if x0 > x1 {
			x0, x1 = x1, x0
		}
		for x := x0; x <= x1; x++ {
			dot(x, y)
		}
	}
	vline := func(x, y0, y1 float64) {
		if y0 > y1 {
			y0, y1 = y1, y0
		}
		for y := y0; y <= y1; y++ {
			dot(x, y)
		}
	}
	// rails
	hline(cx-7*s/32, cx+7*s/32, cy-6*s/32)
	vline(cx-7*s/32, cy-6*s/32, cy+5*s/32)
	vline(cx+7*s/32, cy-6*s/32, cy+5*s/32)
	// carriage
	hline(cx-3*s/32, cx+3*s/32, cy-4*s/32)
	hline(cx-3*s/32, cx+3*s/32, cy-3*s/32)
	// nozzle
	vline(cx, cy-3*s/32, cy+1*s/32)
	dot(cx-1, cy+1*s/32)
	dot(cx+1, cy+1*s/32)
	dot(cx, cy+2*s/32)
	// bed
	hline(cx-6*s/32, cx+6*s/32, cy+5*s/32)
	hline(cx-5*s/32, cx+5*s/32, cy+6*s/32)
}
