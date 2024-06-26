import numpy as np
from math import comb
import matplotlib.pyplot as plt
from scipy import signal
import statsmodels.api as sm
import streamlit as st
import pandas as pd
from io import BytesIO
import openai
# %%


def to_excel(df):
    output = BytesIO()
    # Usa engine='openpyxl' e non chiamare `save` direttamente
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Foglio1')
        # Non è necessario chiamare writer.save()
    processed_data = output.getvalue()
    return processed_data


openai.api_key = st.secrets["OPkey"]


def askAI(domanda):
    risposta = openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {
                "role": "user",
                "content": domanda,
            },
        ],
    )
    resp = risposta.choices[0].message.content
    return resp


Generated = 0
with st.sidebar:
    st.write(
        "Genera un processo ARIMA(p,d,q,S)xSARIMA(0,1,S) per testare l'applicazione")
    p = int(st.number_input('p', step=1, key=1))
    d = int(st.number_input('d', step=1, key=20))
    q = int(st.number_input('q', step=1, key=2))
    S = int(st.number_input('Seasonality (S>1)', step=1, key=110))
    if S > 2:
        A = (st.number_input('Seasonal Amplitude', step=0.1, key=111))
    NN = int(st.number_input('N', min_value=100, step=1, key=100))
    if (p > 0) | (q > 0):
        Generated = 1
        a = np.concatenate([[1], 0.5*np.random.rand(p)-0.5*np.random.rand(p)])
        b = np.concatenate([[1], 0.5*np.random.rand(q)-0.5*np.random.rand(q)])
        st.write('I coefficenti generati sono: ')
        cc1, cc2 = st.columns(2)
        with cc1:
            st.header("AR("+str(p)+"):")
            st.write(a[1:])
        with cc2:
            st.header("MA("+str(q)+"):")
            st.write(b[1:])
        md = "SARIMA ("+str(p)+","+str(d)+","+str(q)+","+str(S)+")"
        YY = pd.DataFrame(sm.tsa.ArmaProcess(
            a, b).generate_sample(NN), columns=["Serie " + md])
        if d > 0:
            for _ in range(d):
                YY = YY.cumsum()
        if S > 1:
            for i in range(0, len(YY)):
                YY.iloc[i] = YY.iloc[i]+A*np.sin(2*np.pi/S*i)

        excel_sint = to_excel(YY)
        st.download_button('Scarica la serie sintetica in excel',
                           data=excel_sint, file_name='test_data.xlsx')


st.header('Linear Model Predictor')
Input_file = st.file_uploader(
    'Upload your file (only .csv or .xlsx files are permitted) or generate a sinthetic series on the sidebar')

if Input_file:
    if Input_file.name.endswith('csv'):
        D = pd.read_csv(Input_file)
    elif Input_file.name.endswith('xlsx'):
        D = pd.read_excel(Input_file, sheet_name=0)
    else:
        st.error('Formato file non supportato')
    st.write('Ecco un estratto del file che hai caricato')
    st.write(D.head(5))
elif Generated == 1:
    D = YY
    st.write("Ecco un estratto dell'ultima serie che hai generato")
    st.write(D.head(5))
# steps to predict
if Input_file or Generated == 1:
    N = int(st.number_input('Quanti periodi vuoi stimare?', step=1, key=4))
    # %%
    Sh = D.shape
    if Sh[1] > Sh[0]:
        D = D.transpose()
    D_n = D.apply(pd.to_numeric, errors='coerce')
    Y = np.array(D_n)
    Y = Y[~np.isnan(Y[:, 0]), :]
    Size = np.shape(Y)
    if N > 0:
        # estimated array: initializing
        Yhat = np.zeros((Size[0]+N+1, Size[1]))
        st.write("Specifica l'ordine del modello (p,d,q,S)")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            p1 = int(st.number_input('p', step=1, key=5))
        with col2:
            d1 = int(st.number_input('d', step=1, key=6))
        with col3:
            q1 = int(st.number_input('q', step=1, key=7))
        ord = (p1, d1, q1)
        with col4:
            S = int(st.number_input(
                'Seasonality (S > 1)', step=1, key=8))
        if S > 1:
            with col4:
                col41, col42, col43 = st.columns(3)
                with col41:
                    ps = int(st.number_input(
                        'ps', step=1, min_value=0, key=50))
                with col42:
                    ds = int(st.number_input(
                        'ds', step=1, min_value=0, key=60))
                with col43:
                    qs = int(st.number_input(
                        'qs', step=1, min_value=0, key=70))
            Sord = (ps, ds, qs, S)
            SmodelName = "SARIMA("+str(ps)+","+str(ds) + \
                ","+str(qs)+","+str(S)+")"
        modelName = "ARIMA("+str(p1)+","+str(d1)+","+str(q1)+")"
        for i in range(0, Size[1]):
            if S > 1:
                model = sm.tsa.ARIMA(Y[:, i], order=ord, seasonal_order=Sord)
            else:
                model = sm.tsa.ARIMA(Y[:, i], order=ord)

            result = model.fit()
            Yhat[:, i] = result.predict(start=0, end=Size[0]+N)
        st.write('I parametri stimati sono: ')
        col1, col2 = st.columns(2)
        with col1:
            st.write(result.param_names)
        with col2:
            st.write(result.params.tolist())
        # %%
        Y2 = np.vstack((Y, np.zeros((N, Size[1]))))
        for j in range(len(Y), len(Yhat)-1):
            for k in range(0, Size[1]):
                Y2[j, k] = Yhat[j+1, k]
        # %%
        fig, axs = plt.subplots(Size[1], 1, figsize=(5, Size[1]*2))
        if Size[1] == 1:
            axs = [axs]
        for k in range(Size[1]):
            ax = axs[k]
            ax.plot(Y2[:, k], color='red', linestyle='--')
            ax.plot(Y[:, k])
            ax.set_title('Serie ' + str(k+1), fontsize=6)
            ax.tick_params(axis='x', labelsize=5)
            ax.tick_params(axis='y', labelsize=5)

        plt.tight_layout()
        st.pyplot(fig, use_container_width=True, clear_figure=True)
        Dh = pd.concat([D, pd.DataFrame(Y2[len(Y2)-N:, :])],
                       ignore_index=True)
        st.write('Serie con previsione')
        st.write(Dh.transpose())
        excel_file = to_excel(Dh.transpose())
        st.download_button('Scarica la serie in excel',
                           data=excel_file, file_name='data.xlsx')

# %%
        stat = st.button('Show Statistics and generate Report', key=12)
        if stat:
            st.write(result.summary())
            Report = "Commenta il seguente report statistico di un modello di analisi di una serie temporale e fornisi suggerimenti su come proseguire" +\
                "Si è stimato un modello "+modelName + "x" + SmodelName +\
                ". Il numero di osservazioni disponibili è: " + str(result.nobs) +\
                ". AIC = "+str(result.aic) + "BIC = " + str(result.bic) + "HQIC = " + str(result.hqic) +\
                ". I parametri stimati sono: " + str(result.param_names) +\
                ". I valori trovati per i parametri sono: " + str(result.params) +\
                ". I livelli di significatività osservata sono: " + str(result.pvalues) +\
                ". Il test sulla noermalità dei residui restituisce il seguente risultato: [Jarque-Brera (JB), Prob(JB), Skew, Kurtosis = " +\
                str(result.test_normality(method='jarquebera'))
            st.header("Statistical Report")
            st.write(askAI(Report))
