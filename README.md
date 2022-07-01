# openmaps_tiler

To use Open Street Map tiles, we need to convert between 3 representations of geolocation data:

1. Longitude and lattitude coordinates (Coordinate)
    * This is what we use in the real world
2. Open Street Map tile coordinates (TilePoint)
    * This is a scaled mapping where the integer portion of the x and y parameters represent a tile grid identifier
3. Tile pixel coordinates (PixelPoint)
    * When the tile coordinates are expanded out to specific pixels in the tile (tiles are 256 * 256 pixels)

Converting between these types allows us to resolve a Coordinate object (lon/lat) to a tile coordinate (for tile retrieval), and then reference a specific pixel in the tile that the original Coordinate object corresponds to.

One complicating factor is that the y-axis for TilePoint and PixelPoint space runs opposite to longitude - as longitude increases, TilePoint and PixelPoint y-values decrease. This has ramifications for bounding boxes