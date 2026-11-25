in vec3 v_pos; in vec3 v_norm; in vec2 v_uv; in vec3 v_obj; in vec3 v_c1; in vec3 v_c2; in vec4 v_par;
flat in int v_mat; flat in vec3 v_seed;
out vec4 frag;

vec3 envReflect(vec3 r, vec3 p, float s){
    vec3 c = r.y > 0. ? skyBase(r) : mix(u_gnd.rgb * .55, skyBase(vec3(r.x, .02, r.z)), smoothstep(-.35, 0., r.y));
    if(ENV==0 || ENV==2 || ENV==4){
        float sp = u_edge.w;
        float k = fract((s + r.z * 9.) / sp);
        float band = smoothstep(.40,.5,k) * smoothstep(.60,.5,k);
        c += (u_lamp.rgb * 2.2 + .15) * band * smoothstep(.15,.6,r.y) * (1.-smoothstep(.75,.98,abs(r.x)));
        c += u_edge.rgb * .55 * smoothstep(.75,.95,abs(r.x)) * smoothstep(-.25,.02,r.y)*smoothstep(.35,.05,r.y);
        c += mix(u_edge2.rgb, u_edge.rgb, step(0., r.x)) * .35 * smoothstep(.3,.9,abs(r.x)) * smoothstep(0.,.3,r.y)
             * step(.5, hash21(floor(vec2((s + r.z*14.)/7., r.y*7.))));
    } else if(ENV==5){
        c += vec3(1.5,1.65,1.9) * smoothstep(.55,.62,r.y) * smoothstep(.95,.88,r.y) * smoothstep(.42,.36,abs(r.x));
        c += vec3(.0,.75,1.0) * 1.1 * smoothstep(.62,.72,-r.x) * smoothstep(.0,.12,r.y)*smoothstep(.5,.3,r.y);
        c += vec3(.55,.25,1.0) * 1.1 * smoothstep(.62,.72,r.x) * smoothstep(.0,.12,r.y)*smoothstep(.5,.3,r.y);
        c += vec3(.5,.55,.7) * smoothstep(.02,.05,r.y)*smoothstep(.12,.08,r.y) * smoothstep(.2,.8,-r.z);
    } else {
        c += vec3(.10) * smoothstep(.2,.8,noise(vec2(r.x*5., (s+r.z*20.)*.12))) * smoothstep(.0,.4,r.y);
    }
    return c;
}

vec3 signPattern(vec2 uv, float seed, vec3 a, vec3 b){
    // Panneau lumineux : cadre, glyphes abstraits, bandeau defilant
    float t = u_cam.w;
    vec2 e = min(uv, 1.-uv);
    float frame = smoothstep(.045,.015,min(e.x,e.y));
    float kind = floor(seed * 4.);
    vec3 c = mix(a,b,uv.y) * .10;
    vec2 g = uv * vec2(4., 8.);
    if(kind < 1.){                                   // colonnes de glyphes
        vec2 id = floor(g), f = fract(g);
        float h = hash21(id + floor(seed*91.));
        float gl = step(.22,f.x)*step(f.x,.82)*step(.2,f.y)*step(f.y,.85);
        vec2 q = floor(f*5.);
        gl *= step(.42, hash21(q + id*7. + floor(h*30.)));
        c += mix(a,b,step(.5,h)) * gl * 2.2;
    } else if(kind < 2.){                            // anneaux
        vec2 q = uv - vec2(.5,.62); q.x *= 1.0;
        float r = length(q);
        c += a * (smoothstep(.03,.0,abs(r-.22)) + smoothstep(.02,.0,abs(r-.30))) * 2.;
        c += b * smoothstep(.02,.0,abs(q.y - .10*sin(q.x*18.+t*3.))) * step(abs(q.x),.4) * 2.;
        c += a * step(uv.y,.26)*step(.12,uv.y)*step(.12,uv.x)*step(uv.x,.12+.76*fract(t*.2+seed)) * 1.6;
    } else if(kind < 3.){                            // bandes diagonales
        float d = fract((uv.x + uv.y*1.6)*3. - t*.6);
        c += mix(a,b,uv.y) * smoothstep(.5,.46,d)*smoothstep(.0,.04,d) * 1.5 * smoothstep(.06,.12,min(e.x,e.y));
    } else {                                         // egaliseur
        float col = floor(uv.x*9.);
        float lv = .25 + .65*noise(vec2(col*3.1+seed*50., t*2.2));
        float bar = step(uv.y, lv)*step(.12,fract(uv.x*9.))*step(.25,fract(uv.y*18.));
        c += mix(a,b,uv.y) * bar * 1.9;
    }
    c += mix(b,a,.5) * frame * 2.4;
    return c * (.86 + .14*sin(t*9.+seed*60.)) * 1.15;
}

void main(){
    vec3 n = normalize(v_norm);
    vec3 cp = u_cam.xyz; cp.y *= u_track.w;
    vec3 view = v_pos - cp;
    float dist = length(view);
    vec3 v = -view / dist;
    if(dot(n, v) < 0.) n = -n;
    float s = u_track.x + v_pos.z;
    int m = v_mat;
    vec3 alb = vec3(.04), emi = vec3(0.);
    float rough = .5, metal = 0., refl = .0, night = 1. - .86*u_sun.w;
    float brake = v_par.x, lights = v_par.y, flash = v_par.z, seed = v_par.w;
    if(m==0){ alb = v_c1; metal = .55; refl = 1.; rough = .22;
        alb *= 1. + .12*(hash21(floor(v_obj.xz*220.)+floor(v_obj.y*220.))-.5)*smoothstep(14.,3.,dist); }
    else if(m==1){ alb = vec3(.008,.010,.016); refl = 1.15; rough = .08; metal=.15; }
    else if(m==2){ float w = step(.5, fract((v_obj.x+v_obj.z)*32.)) * smoothstep(9.,3.,dist); alb = vec3(.013)+.012*w; refl=.28; rough=.4; }
    else if(m==3){ alb = vec3(.72,.74,.78); metal = 1.; refl = 1.; rough=.2; }
    else if(m==4){ alb = vec3(.06,.0,.005); float pulse = .9 + 2.6*brake; emi = vec3(1.,.03,.07) * pulse * (1.1 + .25*lights); }
    else if(m==5){ alb = vec3(.5); emi = vec3(.85,.95,1.1) * (1.1 + 2.0*lights); }
    else if(m==6){ alb = vec3(.02); emi = v_c2 * 2.1; }
    else if(m==7){ alb = vec3(.012); rough=.8; refl=.06; }
    else if(m==8){ alb = vec3(.30,.32,.36); metal=1.; refl=.85; rough=.28; }
    else if(m==9){ alb = vec3(.006); rough=1.; }
    else if(m==10){ emi = v_c1 * 2.2; }
    else if(m==11){ alb = vec3(.02); vec2 g=v_obj.xy; emi = v_c2*.55*step(.018,abs(abs(g.x)-.2)) ; }
    else if(m==12){ alb = v_c2*.8; refl=.7; metal=.3; }
    else if(m==13){                                   // immeubles
        float along = abs(n.x) > .5 ? v_obj.z : v_obj.x;
        vec2 cell = vec2(along / 1.75, v_obj.y / 2.5);
        vec2 id = floor(cell), f = fract(cell);
        float fw = clamp(max(fwidth(cell.x), fwidth(cell.y)), 0., 1.);
        float h = hash21(id + floor(seed*311.) + n.x*13.);
        float fl = hash11(id.y + floor(seed*77.));
        float lit = step(.60 - .25*step(.86,fl), h);
        float win = smoothstep(.10,.16+fw,f.x)*smoothstep(.92,.86-fw,f.x)*smoothstep(.16,.24+fw,f.y)*smoothstep(.90,.82-fw,f.y);
        vec3 wc = mix(mix(vec3(1.,.62,.28), vec3(.45,.75,1.), step(.62,fract(h*17.))), v_c1, step(.80, fract(h*31.)));
        float twk = .75 + .25*sin(u_cam.w*(1.+h*3.)+h*90.);
        alb = vec3(.020,.023,.036) + .012*step(.5,fract(cell.y*1.));
        refl = win*.55; rough=.15;
        emi = wc * win * lit * (.22 + .60*fract(h*7.7)) * twk;
        emi = mix(emi, wc*.16, smoothstep(.35,.9,fw));
        // aretes neon + bandeaux
        float hgt = v_seed.y;
        float top = smoothstep(hgt-.55, hgt-.45, v_obj.y) ;
        float edge = 0.;
        if(seed > .45) edge = top;
        if(seed > .72) edge = max(edge, smoothstep(.985,1.,sin(v_obj.y*.22+seed*40.)*.5+.5));
        emi += mix(v_c1,v_c2,step(.6,fract(seed*9.))) * edge * 1.15 * step(abs(n.y),.5);
        if(abs(n.y) > .5){ emi = vec3(0.); }
        emi *= smoothstep(-.5,3.,v_obj.y)*.95;
        night = 1. - .55*u_sun.w;
    }
    else if(m==14){ float k = noise(v_obj.xz*3.+seed*40.)*.6+.4; alb = v_c1*k; rough=.9; }
    else if(m==15){ float k = fbm(v_obj.xz*.7+v_obj.y*.9+seed*30.); alb = v_c1*(.55+.8*k); rough=.95; }
    else if(m==16){ float sc = .6+.4*sin(v_obj.y*18. - u_cam.w*9.); emi = v_c1 * 1.5*sc; }
    else if(m==17){ emi = signPattern(v_uv, seed, v_c1, v_c2) ; alb=vec3(.01); }
    else if(m==18){ alb = vec3(.055,.035,.022)*(.7+.6*noise(v_obj.xy*vec2(9.,1.5))); rough=.9; }
    else if(m==19){ alb = mix(vec3(.95,.16,.02), vec3(.9), step(.35,v_uv.y)*step(v_uv.y,.6)); emi = alb*.28; }
    else if(m==20){ alb = vec3(.01); refl=1.2; rough=.05; }
    else if(m==21){ alb = vec3(.14,.145,.16)*(.8+.4*noise(v_obj.xz*2.+v_obj.y)); rough=.9; }
    else if(m==22){ float bl = step(.0, sin(u_cam.w*7.+seed*40.)); emi = vec3(1.,.45,.03)*(.35+3.2*bl); }
    else if(m==23){ alb = vec3(.045,.03,.022); rough=.95; }

    vec3 L = normalize(u_sun.xyz);
    float nl = max(dot(n,L),0.);
    vec3 hemi = mix(u_gnd.rgb, u_sky.rgb, n.y*.5+.5);
    vec3 lamp = lampLight(v_pos, s) * (.35+.65*max(n.y*.6+.4,0.));
    vec3 hb = vec3(0.);
    if(u_head.y > 0.) hb = vec3(.85,.93,1.05) * headBeam(v_pos) * u_head.y * (1.2 + 2.4*u_sun.w) * max(-n.z*.8+.35, .0);
    vec3 light = (u_suncol.rgb*nl + hemi*1.25 + lamp*.9) * night + hb;
    vec3 col = alb * (1.-metal*.55) * light;
    vec3 hv = normalize(L+v);
    float spec = pow(max(dot(n,hv),0.), mix(140.,10.,rough)) * (1.-rough);
    col += u_suncol.rgb * spec * night * mix(.6, 1.4, refl);
    if(refl > 0.){
        vec3 r = reflect(-v, n);
        float fr = pow(1.-max(dot(n,v),0.), 4.);
        vec3 env = envReflect(r, v_pos, s) * mix(1.,.25,u_sun.w);
        vec3 f0 = mix(vec3(.05), alb*1.1+.02, metal);
        col += env * mix(f0, vec3(1.), fr*.75) * refl * (1.-rough*.6);
    }
    col += emi;
    col = mix(col, vec3(1.0,.35,.40)*2.2, clamp(flash,0.,1.)*.75);
    if(ENV!=5) col = applyFog(col, dist, -v);
    frag = vec4(col, 1.);
}
