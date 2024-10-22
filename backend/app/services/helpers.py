


def calculate_margin_from_df(df):
    """
    Calculate the margin automatically from the given dataframe

    Args:
        df (dataframe): The compositon dataframe that contains the necessities for calculation of margin

    Returns:
        margin (float): The Calculated margin from the excel file
    """
    return (df['df_MRP_incl_tax'] - df['df_unit_rate_to_hll_incl_of_tax']) / df['df_MRP_incl_tax'] * 100