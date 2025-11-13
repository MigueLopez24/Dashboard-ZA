(function(){
    // Debounce helper
    function debounce(fn, wait){ var t; return function(){ clearTimeout(t); t=setTimeout(fn, wait); }; }

    function resizeAllPlots(){
        if (typeof Plotly === 'undefined') return;
        var plots = document.querySelectorAll('.js-plotly-plot');
        plots.forEach(function(p){
            try{
                if (p.offsetWidth > 0 && p.offsetHeight > 0){
                    Plotly.Plots.resize(p);
                }
            }catch(e){}
        });
    }

    // --- Ajuste seguro de tablas VPN sin reparentar nodos ---
    function getInnerElement(container){
        if (!container) return null;
        // Si el servidor ya renderizó un wrapper .vpn-inner úsalo.
        var vpnInner = container.querySelector('.vpn-inner');
        if (vpnInner) return vpnInner;
        // Si no, usa el primer hijo del container SIN moverlo.
        return container.firstElementChild;
    }

    function adjustVpnTables(){
        var containers = document.querySelectorAll('.internet-detail-vpn-table');
        containers.forEach(function(container){
            try{
                var inner = getInnerElement(container);
                if (!inner) return;

                // Limpiar transform previo para medir contenido real
                inner.style.transform = '';
                inner.style.width = '';

                var availH = container.clientHeight || (window.innerHeight * 0.25);
                var availW = container.clientWidth || (window.innerWidth - 40);
                var contentH = inner.scrollHeight || inner.offsetHeight || 0;
                var contentW = inner.scrollWidth || inner.offsetWidth || 0;

                if (contentH === 0 || isNaN(contentH)) return;

                // calcular escala basada en altura y anchura
                var scaleH = availH / contentH;
                var scaleW = (contentW > 0) ? (availW / contentW) : 1;
                var scale = Math.min(1, scaleH, scaleW);

                // Aplicar transform directamente sobre el elemento (sin moverlo)
                inner.style.transformOrigin = 'top left';
                inner.style.transform = 'scale(' + scale + ')';

                // Ajuste de ancho compensatorio para mantener flujo de layout si es necesario
                if (scale < 1 && contentW > 0){
                    // Al escalar, el elemento ocupa menos espacio visual; para evitar recortes laterales,
                    // aumentamos su ancho real (no reparentando). Esto no mueve nodos.
                    inner.style.width = (100 / scale) + '%';
                } else {
                    inner.style.width = '100%';
                }

            }catch(e){
                console.error('adjustVpnTables error', e);
            }
        });
    }

    var debouncedResize = debounce(function(){
        resizeAllPlots();
        adjustVpnTables();
    }, 120);

    var observer = new MutationObserver(function(){ debouncedResize(); });
    observer.observe(document.body, { attributes: true, childList: true, subtree: true, attributeFilter: ['style','class'] });

    window.addEventListener('resize', debouncedResize);
    document.addEventListener('visibilitychange', debouncedResize);

    // Initial delayed resize to catch late renders
    setTimeout(function(){ resizeAllPlots(); adjustVpnTables(); }, 500);
    setTimeout(function(){ resizeAllPlots(); adjustVpnTables(); }, 1200);
})();
