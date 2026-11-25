in vec2 v_ndc;
out vec4 frag;

float ridge(float a, float f, float seed){ return fbm(vec2(a*f+seed, seed*3.1)); }

void main(){
    vec3 d = normalize(u_fwd.xyz + u_right.xyz*v_ndc.x*u_right.w + u_up.xyz*v_ndc.y*u_up.w);
    if(u_track.w < 0.) d.y = -d.y;
    d.y += u_res.z * .9;
    float az = atan(d.x, d.z) + u_fwd.w;
    vec3 c = skyBase(d);
    float nt = mix(1., .12, u_sun.w);
    float t = u_cam.w;
    if(ENV==0 || ENV==2){
        // etoiles
        vec2 g = vec2(az*150., d.y*190.); vec2 id = floor(g);
        float st = step(.988, hash21(id)) * smoothstep(.45,.0,length(fract(g)-.5)) * smoothstep(.12,.5,d.y);
        c += st*(.35+.35*sin(t*2.+hash21(id)*40.)) * (ENV==0 ? 1. : .25);
        // nuages bas eclaires
        float cl = fbm(vec2(az*2.2 + t*.006, d.y*7.));
        c += (ENV==0 ? vec3(.10,.03,.20) : vec3(.20,.05,.14)) * smoothstep(.42,.9,cl) * smoothstep(.0,.12,d.y) * smoothstep(.6,.1,d.y) * .8 * nt;
        if(ENV==0){ // astre neon strie
            vec2 q = vec2(az - .18, d.y - .17);
            float r = length(q);
            float cut = smoothstep(.0,.004, abs(fract((q.y+.13)*28.)-.5)-.02-.20*smoothstep(.06,-.13,q.y));
            vec3 sc = mix(vec3(1.,.10,.42), vec3(.45,.30,1.3), smoothstep(-.11,.11,q.y));
            c += sc * smoothstep(.135,.130,r) * cut * .95 * nt;
            c += vec3(.35,.10,.55) * exp(-r*9.) * .55 * nt;
            // projecteurs
            for(int i=0;i<3;i++){
                float a0 = -1.1 + float(i)*1.05 + .22*sin(t*.22+float(i)*2.);
                float w = abs(az - a0 - (d.y)*(.35*sin(t*.31+float(i)*1.7)));
                c += vec3(.10,.35,.55) * smoothstep(.030,.0,w) * exp(-d.y*3.2) * smoothstep(0.,.06,d.y) * .35 * nt;
            }
        } else {   // tour lumineuse
            float x = (az + .30); float h = d.y;
            float body = smoothstep(.034,.030, abs(x) + h*.105) * step(h,.285);
            float lat = step(.45, fract((h*46.))) * .5 + .5;
            c = mix(c, vec3(1.2,.22,.10)*(.35+.9*lat), body*.9*nt);
            c += vec3(1.,.15,.12)*exp(-abs(x)*22.)*exp(-h*5.)*.35*nt;
            c += vec3(1.6,.3,.2)*smoothstep(.012,.0,length(vec2(x,h-.29)))*(.5+.5*sin(t*3.))*nt;
        }
        // silhouettes urbaines, deux plans
        for(int k=0;k<2;k++){
            float f = k==0 ? 42. : 26.;
            float id2 = floor(az*f + float(k)*37.);
            float hh = (k==0 ? .050 : .035) + (k==0?.095:.075)*pow(hash11(id2+3.*float(k)),2.);
            float in_b = step(d.y, hh) * step(-.2, d.y);
            vec3 bc = (k==0 ? vec3(.030,.028,.080) : vec3(.014,.015,.042)) + u_fog.rgb*.35;
            vec2 wg = vec2(az*f*7., d.y*210.); 
            float w = step(.72, hash21(floor(wg)+id2)) * step(.2,fract(wg.x))*step(.25,fract(wg.y));
            vec3 wc = mix(vec3(1.,.65,.3), mix(vec3(0.,.8,1.),vec3(1.,.15,.6),step(.5,hash11(id2*1.7))), step(.5,hash11(id2)));
            bc += wc*w*(k==0?.12:.20);
            bc += wc*smoothstep(.0035,.0,abs(d.y-hh))*.5*step(.6,hash11(id2*2.3));
            c = mix(c, bc*nt, in_b);
        }
    } else if(ENV==1){
        vec3 sd = normalize(u_sun.xyz); float k = dot(d, sd);
        float r = acos(clamp(k,-1.,1.));
        c += vec3(2.2,.85,.20)*smoothstep(.105,.098,r) * (.75+.35*smoothstep(-.1,.1,d.y-sd.y)) * nt;
        c += vec3(1.4,.45,.12)*exp(-r*5.5)*.75*nt;
        float cl = fbm(vec2(az*1.7+t*.003, d.y*13.));
        c = mix(c, vec3(1.5,.42,.30), smoothstep(.50,.85,cl)*smoothstep(.02,.10,d.y)*smoothstep(.42,.12,d.y)*.55*nt);
        for(int k2=0;k2<3;k2++){
            float fk = float(k2);
            float h = .015 + (.085-.022*fk)*ridge(az, 2.6+fk*1.6, 3.+fk*7.);
            float mesa = floor(h*70.)/70.; h = mix(h, mesa, .55);
            vec3 mc = mix(vec3(.80,.30,.24), vec3(.17,.06,.10), (fk+.6)/3.);
            c = mix(c, mc*nt, smoothstep(.0015,-.0015,d.y-h));
        }
    } else if(ENV==3){
        vec3 sd = normalize(u_sun.xyz); float r = acos(clamp(dot(d,sd),-1.,1.));
        c += u_suncol.rgb*1.6*smoothstep(.040,.034,r)*nt + u_suncol.rgb*.30*exp(-r*7.)*nt;
        float cl = fbm(vec2(az*2.0+t*.004, d.y*8.)+3.);
        c = mix(c, mix(vec3(1.), u_suncol.rgb*.7, .5), smoothstep(.50,.9,cl)*smoothstep(.06,.22,d.y)*.55*nt);
        for(int k2=0;k2<4;k2++){
            float fk = float(k2);
            float h = .22 - fk*.062 + (.20-.035*fk)*(ridge(az, 2.2+fk*1.3, 11.+fk*5.)-.5) + .012*noise(vec2(az*55.+fk*9.,1.));
            vec3 mc = mix(u_fog.rgb*1.05, vec3(.045,.085,.085), (fk+.35)/4.);
            float snow = smoothstep(.012,.05,d.y-(h-.085+.05*noise(vec2(az*26.,d.y*36.)))) * (k2<2?1.:0.);
            float lit = smoothstep(-.3,.6, ridge(az+.01,9.,11.+fk*5.)-ridge(az-.01,9.,11.+fk*5.)+.15);
            mc = mix(mc, vec3(.85,.90,1.)*mix(.55,1.05,lit)*(.35+.65*u_suncol.rgb*.5), snow*.9);
            c = mix(c, mc*nt, smoothstep(.0012,-.0012,d.y-h));
        }
    } else if(ENV==5){
        c += vec3(.015,.05,.08)*exp(-abs(d.y-.02)*14.)*.7;
        c += vec3(.05,.015,.10)*exp(-length(vec2(az*.8-.6,d.y-.25))*3.)*.6;
        float gl = smoothstep(.012,.0,abs(fract(az*6.)-.5))*smoothstep(.35,.0,d.y)*step(0.,d.y);
        c += vec3(.0,.25,.35)*gl*.25;
    }
    frag = vec4(max(c,0.), 1.);
}
