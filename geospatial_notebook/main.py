from __future__ import annotations

from io import BytesIO
from typing import Dict, Tuple

import folium
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import streamlit as st
from folium.raster_layers import ImageOverlay
from PIL import Image
from rasterio.io import MemoryFile
from rasterio.transform import array_bounds
from rasterio.warp import (
    Resampling,
    calculate_default_transform,
    reproject,
    transform_bounds,
)
from streamlit_folium import st_folium


BANDS = ("Green", "Red", "RedEdge", "NIR")
DATE_LABELS = ("Date 1 — baseline", "Date 2 — comparison")


st.set_page_config(page_title="Wetland & Vegetation Monitor", layout="wide")
st.title("Wetland & Vegetation Monitor")
st.caption(
    "A small Streamlit interface for checking eight single-band GeoTIFFs, "
    "calculating NDVI for two dates, and viewing NDVI change."
)

st.info(
    "This tool calculates NDVI from Red and NIR bands. Green and RedEdge are "
    "accepted and checked, but are not used in the NDVI formula. Results are "
    "indicators, not a definitive diagnosis of wetland degradation."
)



def read_uploaded_tif(uploaded_file) -> Tuple[np.ndarray, dict]:
    """Read one uploaded single-band GeoTIFF from its in-memory bytes."""
    if uploaded_file is None:
        raise ValueError("A file is missing.")

    with MemoryFile(uploaded_file.getvalue()) as memfile:
        with memfile.open() as src:
            if src.count != 1:
                raise ValueError(
                    f"{uploaded_file.name} has {src.count} bands; expected 1."
                )
            if src.crs is None:
                raise ValueError(f"{uploaded_file.name} has no CRS metadata.")

            array = src.read(1).astype("float32")
            nodata = src.nodata
            if nodata is not None:
                if np.isnan(nodata):
                    array[~np.isfinite(array)] = np.nan
                else:
                    array[array == nodata] = np.nan

            metadata = {
                "crs": src.crs,
                "transform": src.transform,
                "width": src.width,
                "height": src.height,
                "bounds": src.bounds,
                "nodata": nodata,
                "profile": src.profile.copy(),
            }
    return array, metadata


def same_grid(meta_a: dict, meta_b: dict) -> bool:
    return (
        meta_a["crs"] == meta_b["crs"]
        and meta_a["transform"] == meta_b["transform"]
        and meta_a["width"] == meta_b["width"]
        and meta_a["height"] == meta_b["height"]
    )


def align_to_reference(array: np.ndarray, source_meta: dict, ref_meta: dict) -> np.ndarray:
    """Reproject/resample an array onto the reference raster grid."""
    output = np.full(
        (ref_meta["height"], ref_meta["width"]), np.nan, dtype="float32"
    )
    reproject(
        source=array,
        destination=output,
        src_transform=source_meta["transform"],
        src_crs=source_meta["crs"],
        src_nodata=np.nan,
        dst_transform=ref_meta["transform"],
        dst_crs=ref_meta["crs"],
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    return output


def calculate_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    denominator = nir + red
    result = np.full(red.shape, np.nan, dtype="float32")
    valid = np.isfinite(red) & np.isfinite(nir) & (denominator != 0)
    result[valid] = (nir[valid] - red[valid]) / denominator[valid]
    return result


# def make_preview_png(array: np.ndarray, vmin: float, vmax: float) -> bytes:
#     """Create a small color preview for the Folium map."""
#     cmap = plt.get_cmap("RdYlGn")
#     normalized = np.clip((array - vmin) / (vmax - vmin), 0, 1)
#     rgba = cmap(np.nan_to_num(normalized, nan=0.0))
#     rgba[~np.isfinite(array), 3] = 0
#     image_array = (rgba * 255).astype("uint8")
#     image = Image.fromarray(image_array, mode="RGBA")
#     buffer = BytesIO()
#     image.save(buffer, format="PNG")
#     return buffer.getvalue()

def make_preview_image(
    array: np.ndarray,
    vmin: float,
    vmax: float
) -> str:
    """Create a JSON-compatible Base64 PNG data URL."""

    cmap = plt.get_cmap("RdYlGn")

    normalized = np.clip(
        (array - vmin) / (vmax - vmin),
        0,
        1
    )

    rgba = cmap(
        np.nan_to_num(normalized, nan=0.0)
    )

    # Make NoData pixels transparent
    rgba[~np.isfinite(array), 3] = 0

    image_array = (rgba * 255).astype("uint8")
    image = Image.fromarray(image_array, mode="RGBA")

    # Convert the PIL image to PNG bytes
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    # Convert PNG bytes into a Base64 string
    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    # Return a string that Folium can use as an image source
    return f"data:image/png;base64,{encoded}"

def add_raster_overlay(
    map_object: folium.Map,
    array: np.ndarray,
    reference_meta: dict,
    layer_name: str,
    vmin: float,
    vmax: float,
    show: bool = False,
) -> None:
    height, width = array.shape
    bounds = array_bounds(height, width, reference_meta["transform"])
    max_side = 800
    scale = min(1.0, max_side / max(height, width))
    out_height = max(1, int(height * scale))
    out_width = max(1, int(width * scale))

    dst_transform, _, _ = calculate_default_transform(
        reference_meta["crs"],
        "EPSG:4326",
        width,
        height,
        *bounds,
        dst_width=out_width,
        dst_height=out_height,
    )
    preview = np.full((out_height, out_width), np.nan, dtype="float32")
    reproject(
        source=array,
        destination=preview,
        src_transform=reference_meta["transform"],
        src_crs=reference_meta["crs"],
        src_nodata=np.nan,
        dst_transform=dst_transform,
        dst_crs="EPSG:4326",
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    west, south, east, north = array_bounds(
        out_height, out_width, dst_transform
    )
    ImageOverlay(
    image=make_preview_image(preview, vmin, vmax),
    bounds=[[south, west], [north, east]],
    name=layer_name,
    opacity=0.75,
    show=show,
).add_to(map_object)


def file_inputs(date_title: str, key_prefix: str) -> Dict[str, object]:
    st.subheader(date_title)
    cols = st.columns(4)
    uploads = {}
    for column, band in zip(cols, BANDS):
        with column:
            uploads[band] = st.file_uploader(
                f"{band} band (.tif/.tiff)",
                type=["tif", "tiff"],
                key=f"{key_prefix}_{band}",
                help=f"Upload the single-band {band} GeoTIFF for this date.",
            )
    return uploads


date1_uploads = file_inputs(DATE_LABELS[0], "date1")
date2_uploads = file_inputs(DATE_LABELS[1], "date2")


# APPLICATION STATE


if "wetland_result" not in st.session_state:
    st.session_state["wetland_result"] = None

if "wetland_error" not in st.session_state:
    st.session_state["wetland_error"] = None



# ANALYSIS BUTTON


run_analysis = st.button(
    "Validate & compare",
    type="primary",
    use_container_width=True,
)

if run_analysis:

    # Clear the previous result before starting a new analysis.
    st.session_state["wetland_result"] = None
    st.session_state["wetland_error"] = None

    all_uploads = {
        "Date 1": date1_uploads,
        "Date 2": date2_uploads,
    }

    missing = [
        f"{date_label} — {band}"
        for date_label, band_uploads in all_uploads.items()
        for band, uploaded in band_uploads.items()
        if uploaded is None
    ]

    if missing:
        st.session_state["wetland_error"] = (
            "Please upload all eight files before running "
            "the comparison. Missing: "
            + ", ".join(missing)
        )

    else:
        try:

        
            # READ THE RASTERS
          

            data1 = {}
            meta1 = {}

            data2 = {}
            meta2 = {}

            with st.spinner(
                "Reading and validating GeoTIFF files..."
            ):

                for band in BANDS:

                    data1[band], meta1[band] = (
                        read_uploaded_tif(
                            date1_uploads[band]
                        )
                    )

                    data2[band], meta2[band] = (
                        read_uploaded_tif(
                            date2_uploads[band]
                        )
                    )


           
            # VALIDATION REPORT
            

            validation_rows = []

            for date_label, data, metadata in (
                ("Date 1", data1, meta1),
                ("Date 2", data2, meta2),
            ):

                reference = metadata["Red"]

                for band in BANDS:

                    matches = same_grid(
                        metadata[band],
                        reference,
                    )

                    validation_rows.append(
                        {
                            "Date": date_label,
                            "Band": band,
                            "Grid matches Red": matches,
                            "Dimensions": (
                                f'{metadata[band]["width"]} × '
                                f'{metadata[band]["height"]}'
                            ),
                            "CRS": str(
                                metadata[band]["crs"]
                            ),
                            "Valid pixels": int(
                                np.isfinite(
                                    data[band]
                                ).sum()
                            ),
                        }
                    )


           
            # ALIGN THE RASTERS
       

            # Date 1 Red defines the analysis grid.
            reference_meta = meta1["Red"]

            date1_aligned = {

                band: (
                    data1[band]

                    if same_grid(
                        meta1[band],
                        reference_meta,
                    )

                    else align_to_reference(
                        data1[band],
                        meta1[band],
                        reference_meta,
                    )

                )

                for band in BANDS
            }


            date2_aligned = {

                band: align_to_reference(
                    data2[band],
                    meta2[band],
                    reference_meta,
                )

                for band in BANDS
            }


           
            #  CALCULATE NDVI
            

            ndvi1 = calculate_ndvi(
                date1_aligned["Red"],
                date1_aligned["NIR"],
            )

            ndvi2 = calculate_ndvi(
                date2_aligned["Red"],
                date2_aligned["NIR"],
            )

            ndvi_change = ndvi2 - ndvi1


           
            #  CREATE THE FOLIUM MAP
          

            west, south, east, north = transform_bounds(
                reference_meta["crs"],
                "EPSG:4326",
                *reference_meta["bounds"],
            )

            center = [
                (south + north) / 2,
                (west + east) / 2,
            ]

       
            # Create map_object BEFORE saving it in session_state.

            map_object = folium.Map(
                location=center,
                zoom_start=13,
                tiles="OpenStreetMap",
            )


            # Date 1 NDVI
            add_raster_overlay(
                map_object,
                ndvi1,
                reference_meta,
                "NDVI — Date 1",
                -1,
                1,
                show=True,
            )


            # Date 2 NDVI
            add_raster_overlay(
                map_object,
                ndvi2,
                reference_meta,
                "NDVI — Date 2",
                -1,
                1,
            )


            # NDVI change
            add_raster_overlay(
                map_object,
                ndvi_change,
                reference_meta,
                "NDVI Change",
                -2,
                2,
            )


            folium.LayerControl(
                collapsed=False
            ).add_to(map_object)


            #  DOWNLOAD
            

            output_profile = (
                reference_meta["profile"].copy()
            )

            output_profile.update(
                count=1,
                dtype="float32",
                nodata=np.nan,
                compress="deflate",
            )

            with MemoryFile() as memory_file:

                with memory_file.open(
                    **output_profile
                ) as destination:

                    destination.write(
                        ndvi_change.astype("float32"),
                        1,
                    )

                output_tif = memory_file.read()


            
            #  SAVE EVERYTHING IN SESSION STATE
            

            # Save only AFTER all objects have been created.

            st.session_state["wetland_result"] = {

                "validation_rows": validation_rows,

                "ndvi1": ndvi1,

                "ndvi2": ndvi2,

                "ndvi_change": ndvi_change,

                "map_object": map_object,

                "output_tif": output_tif,

            }


        except Exception as error:

            st.session_state["wetland_error"] = str(
                error
            )


# DISPLAY ERROR


if st.session_state["wetland_error"]:

    st.error(
        "Could not process the uploaded data: "
        + st.session_state["wetland_error"]
    )

    st.caption(
        "Check that the files are readable single-band "
        "GeoTIFFs with CRS metadata and compatible "
        "geographic coverage."
    )


# DISPLAY SAVED RESULTS


result = st.session_state["wetland_result"]


if result is not None:

    st.success(
        "Files loaded. Validation and NDVI comparison completed."
    )


    # VALIDATION SUMMARY


    st.subheader("Validation summary")

    st.dataframe(
        result["validation_rows"],
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Grid mismatch means a band was resampled to the "
        "Date 1 Red reference grid. This does not verify "
        "source accuracy, cloud/shadow quality, or "
        "reflectance calibration."
    )


    # NDVI MAPS

    ndvi1 = result["ndvi1"]

    ndvi2 = result["ndvi2"]

    ndvi_change = result["ndvi_change"]


    st.subheader("NDVI maps")

    col1, col2 = st.columns(2)


    with col1:

        fig, ax = plt.subplots(
            figsize=(6, 5)
        )

        image = ax.imshow(
            ndvi1,
            cmap="RdYlGn",
            vmin=-1,
            vmax=1,
        )

        ax.set_title("NDVI — Date 1")

        ax.axis("off")

        fig.colorbar(
            image,
            ax=ax,
            shrink=0.8,
        )

        st.pyplot(
            fig,
            clear_figure=True,
        )

        plt.close(fig)


    with col2:

        fig, ax = plt.subplots(
            figsize=(6, 5)
        )

        image = ax.imshow(
            ndvi2,
            cmap="RdYlGn",
            vmin=-1,
            vmax=1,
        )

        ax.set_title("NDVI — Date 2")

        ax.axis("off")

        fig.colorbar(
            image,
            ax=ax,
            shrink=0.8,
        )

        st.pyplot(
            fig,
            clear_figure=True,
        )

        plt.close(fig)


    # NDVI CHANGE

    st.subheader(
        "NDVI change (Date 2 − Date 1)"
    )

    fig, ax = plt.subplots(
        figsize=(8, 5)
    )

    image = ax.imshow(
        ndvi_change,
        cmap="RdYlGn",
        vmin=-2,
        vmax=2,
    )

    ax.set_title("NDVI change")

    ax.axis("off")

    fig.colorbar(
        image,
        ax=ax,
        shrink=0.8,
        label="NDVI difference",
    )

    st.pyplot(
        fig,
        clear_figure=True,
    )

    plt.close(fig)


    # STATISTICS

    valid = ndvi_change[
        np.isfinite(ndvi_change)
    ]

    metric_cols = st.columns(4)


    metric_cols[0].metric(
        "Valid pixels",
        f"{valid.size:,}",
    )


    metric_cols[1].metric(
        "Mean change",
        (
            f"{float(valid.mean()):.4f}"
            if valid.size
            else "N/A"
        ),
    )


    metric_cols[2].metric(
        "Increased pixels",
        (
            f"{int((valid > 0).sum()):,}"
            if valid.size
            else "N/A"
        ),
    )


    metric_cols[3].metric(
        "Decreased pixels",
        (
            f"{int((valid < 0).sum()):,}"
            if valid.size
            else "N/A"
        ),
    )


    # INTERACTIVE MAP
   

    st.subheader("Interactive map")

    st_folium(
        result["map_object"],
        use_container_width=True,
        height=600,
        key="wetland_ndvi_map",
    )


   
    # DOWNLOAD NDVI CHANGE
    

   
    # DOWNLOAD A VISUAL PNG PREVIEW
    

    st.subheader("Download visual preview")

    ndvi_change = result["ndvi_change"]

    valid = ndvi_change[np.isfinite(ndvi_change)]

    if valid.size > 0:

        # Use the actual data range for display.
        vmin = float(valid.min())
        vmax = float(valid.max())

        # Avoid a zero-width display range.
        if vmin == vmax:
            vmax = vmin + 0.001

        fig, ax = plt.subplots(figsize=(7, 6))

        image = ax.imshow(
            ndvi_change,
            cmap="RdYlGn",
            vmin=vmin,
            vmax=vmax,
        )

        ax.set_title("NDVI Change (Date 2 − Date 1)")
        ax.axis("off")

        fig.colorbar(
            image,
            ax=ax,
            label="NDVI difference",
            shrink=0.8,
        )

        # Save the visualization as PNG bytes.
        png_buffer = BytesIO()

        fig.savefig(
            png_buffer,
            format="PNG",
            bbox_inches="tight",
            dpi=150,
        )

        png_buffer.seek(0)

        plt.close(fig)

        st.download_button(
            "Download NDVI change preview (.png)",
            data=png_buffer.getvalue(),
            file_name="ndvi_change_preview.png",
            mime="image/png",
            use_container_width=True,
            key="download_ndvi_change_png",
        )

    else:
        st.warning("No valid NDVI-change pixels are available.")
     
    # DEBUG: INSPECT THE GENERATED TIFF
    

    import io

    with rasterio.open(
        io.BytesIO(result["output_tif"])
    ) as src:

        data = src.read(1, masked=True)

        st.write("Raster shape:", data.shape)
        st.write("Data type:", data.dtype)
        st.write("CRS:", src.crs)
        st.write("NoData:", src.nodata)
        st.write("Valid pixels:", int(data.count()))

        if data.count() > 0:
            st.write("Minimum:", float(data.min()))
            st.write("Maximum:", float(data.max()))
        else:
            st.warning("The TIFF contains no valid pixels.")
